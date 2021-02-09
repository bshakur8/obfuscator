from functools import partial

from detectors.detectors import LowLevelFilth, MyCredentialFilth
from strategy import utils
from strategy.abs_file_splitter import FileSplitters
from strategy.workers import ObfuscateWorker
from strategy.workers_pool import WorkersPool

SED_SEPARATOR = '@'
SED_FORBIDDEN_CHARS = "[]*^" + SED_SEPARATOR


class ObfuscateLowLevel(FileSplitters):
    def __init__(self, args, name=None, threshold=None):
        super().__init__(args, name or "LowLevel")
        self.low_level_filths = []
        self.file_to_filth_segment = {}
        self.threshold = threshold

    @staticmethod
    def clean_suffix(string, chars):
        return string.rstrip(chars).strip()

    def pre_all(self):
        super().pre_all()
        ip_regex = r"([0-9]{1,3}[\.]){3}[0-9]{1,3}"
        file_regex = r"""(/[^ \"']+)+"""
        credentials_regex = MyCredentialFilth.regex_str
        mac_addr_regex = r"([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}"

        kwargs = {'salt': self.args.salt}

        # Order is important! ip can be inside a file dir but not vise-versa
        self.low_level_filths = [
            [
                LowLevelFilth(placeholder="FILE-DIR", regex=file_regex, **kwargs),
                LowLevelFilth(placeholder="CREDENTIALS", regex=credentials_regex, **kwargs),
                LowLevelFilth(placeholder="MAC-ADDR", regex=mac_addr_regex, **kwargs),
            ],
            [
                LowLevelFilth(placeholder="IP-PORT", regex=ip_regex, **kwargs),
            ],
        ]

    def obfuscate_one(self, abs_file, **kwargs):
        self._print(abs_file)

        cmds = []
        for filth, segments in self.file_to_filth_segment[abs_file].items():
            for segment in segments:
                obf_segment = filth.replace_with(segment)
                for t in SED_FORBIDDEN_CHARS:
                    segment = segment.replace(t, fr'\{t}')
                cmds.append(f's{SED_SEPARATOR}{segment}{SED_SEPARATOR}{obf_segment}{SED_SEPARATOR}g')

        size = int(self.args.threshold / 10)
        for i in range(0, len(cmds), size):
            chunk = cmds[i:i + size]
            cmd = "sed -i '{}' {}".format(" ; ".join(chunk), abs_file)
            _ = utils.run_local_cmd(cmd=cmd, log_output=False, log_input=True)
        return abs_file

    def iter_filth(self, src_file):
        assert self.low_level_filths
        kwargs = dict(log_output=False, log_input=True)
        grep_cmd = 'grep -wPo "{r}" {f} | sort -u'
        key_to_func = {filth: partial(utils.run_local_cmd, cmd=grep_cmd.format(r=filth.regex, f=src_file), **kwargs)
                       for filths in self.low_level_filths for filth in filths}

        filth_to_segment = {}
        for filth, res in WorkersPool.futures_pool(key_to_func, len(key_to_func)):
            try:
                if filth_to_segment[filth] is None:
                    continue  # already deleted: above threshold
            except KeyError:
                filth_to_segment[filth] = []

            segments = set(seg for seg in res.stdout.split("\n") if seg)
            filth_to_segment[filth] += segments
            if len(filth_to_segment[filth]) > self.threshold:
                utils.logger.info(f"LowLevel: Exclude {src_file}: {len(filth_to_segment[filth])} segments")
                filth_to_segment[filth] = None  # mark is deleted
                yield False
                raise StopIteration  # stop checking for more filths and move to next file

        # Finished all checks - we can return True
        if any(filth_to_segment.values()):
            num_segments = sum(len(x) for x in filth_to_segment.values())
            utils.logger.info(f"LowLevel: Include {src_file}: {num_segments} segments")

            # Fix segments inside filth_to_segment
            for filth, segments in filth_to_segment.items():
                segments = set(self.clean_suffix(seg, "'") for seg in segments)
                filth_to_segment[filth] = sorted(segments, key=lambda x: -len(x))

            self.file_to_filth_segment[src_file] = filth_to_segment
            # Handle by low level strategy
            yield True

        # No segments - no need to handle
        raise StopIteration

    def orchestrate_workers(self, raw_files, *args, **kwargs):
        strategy_to_worker = kwargs.get('strategy_to_worker')
        assert strategy_to_worker

        low_level_worker = strategy_to_worker[True]  # type: ObfuscateWorker
        other_strategy_worker = strategy_to_worker[False]  # type: ObfuscateWorker

        key_to_func = {src_file: partial(self.iter_filth, src_file) for src_file in raw_files}

        for src_file, itr in WorkersPool.futures_pool(key_to_func, len(key_to_func)):
            for keep_here in itr:
                if keep_here:
                    low_level_worker.put(src_file)
                else:
                    other_strategy_worker.put(src_file)

        utils.logger.info("Finish orchestrate workers")
        low_level_worker.join()
        other_strategy_worker.join()

