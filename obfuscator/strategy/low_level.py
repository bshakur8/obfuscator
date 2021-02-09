from collections import defaultdict

from detectors.detectors import LowLevelFilth, MyCredentialFilth
from strategy import utils
from strategy.abs_file_splitter import FileSplitters

SED_SEPARATOR = '@'
SED_FORBIDDEN_CHARS = "[]*^" + SED_SEPARATOR


class ObfuscateLowLevel(FileSplitters):
    def __init__(self, args, name=None):
        super().__init__(args, name or "LowLevel")
        self.low_level_filths = []
        self.file_to_filth_segment = {}
        self.threshold = args.threshold

    @staticmethod
    def clean_suffix(string, chars):
        return string.rstrip(chars).strip()

    def pre_all(self):
        super().pre_all()
        ip_regex = r"([1-9]{1,3}\.([0-9]{1,3}[\.]){2}[0-9]{1,3})"
        file_regex = r"""(/[^ \"']+)+"""
        credentials_regex = MyCredentialFilth.regex_str
        mac_addr_regex = r"([a-f0-9A-F]{2}:){5}[a-f0-9A-F]{2}"

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

    def obfuscate_one(self, *args, **kwargs):
        abs_file, filth_to_segment = args[0]
        self._print(abs_file)

        cmds = []
        for filth, segments in filth_to_segment.items():
            for segment in segments:
                obf_segment = filth.replace_with(segment)
                for t in SED_FORBIDDEN_CHARS:
                    segment = segment.replace(t, fr'\{t}')
                cmds.append(f's{SED_SEPARATOR}{segment}{SED_SEPARATOR}{obf_segment}{SED_SEPARATOR}g')

        for chunk in utils.chunkify(cmds, size=min(50, int(self.args.threshold / 5))):
            cmd = "{} '{}' {}".format(self.args.sed, " ; ".join(chunk), abs_file)
            _ = utils.run_local_cmd(cmd=cmd, log_output=self.args.debug_prints, log_input=True)
        return abs_file

    def orchestrate_iterator(self, src_file, *args, **kwargs):
        assert self.low_level_filths
        log_kwargs = dict(log_output=self.args.debug_prints, log_input=self.args.debug_prints)
        grep = f'{self.args.grep} "{{r}}" {src_file} | sort -u'

        filth_to_segment = defaultdict(list)
        total_segments = 0
        for filths in self.low_level_filths:
            for filth in filths:
                res = utils.run_local_cmd(grep.format(r=filth.regex), **log_kwargs)
                segments = set(s for s in res.stdout.split("\n") if s)
                total_segments += len(segments)
                filth_to_segment[filth] += segments

                if total_segments >= self.threshold:
                    utils.logger.info(f"LowLevel: Exclude {src_file}: {total_segments} segments")
                    return src_file, False, {}

        # Finished all checks - we can return True
        if total_segments:
            utils.logger.info(f"LowLevel: Include {src_file}: {total_segments} segments")
            for filth, segments in filth_to_segment.items():
                segments = sorted(set(self.clean_suffix(seg, "'") for seg in segments), key=lambda x: -len(x))
                filth_to_segment[filth] = segments

            self.file_to_filth_segment[src_file] = filth_to_segment
            return src_file, True, dict(filth_to_segment)

        # No segments - no need to handle
        return src_file, None, {}
