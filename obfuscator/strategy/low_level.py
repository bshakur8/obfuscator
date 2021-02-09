from collections import defaultdict

from detectors.detectors import LowLevelFilth, MyCredentialFilth
from strategy import utils
from strategy.abs_file_splitter import FileSplitters

SED_SEPARATOR = '@'
SED_FORBIDDEN_CHARS = "[]*"+SED_SEPARATOR


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
        file_regex = r"""(\B)(/[^ \"']+)+(\>|\w)"""
        credentials_regex = MyCredentialFilth.regex_str
        mac_addr_regex = r"(^|\W)([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}($|\w)"

        kwargs = {'salt': self.args.salt}

        # Order is important!
        self.low_level_filths = [
            [
                LowLevelFilth(placeholder="FILE-DIR", regex=file_regex, **kwargs),
                LowLevelFilth(placeholder="CREDENTIALS", regex=credentials_regex, **kwargs),
                LowLevelFilth(placeholder="MAC-ADDR", regex=mac_addr_regex, **kwargs),
            ],
            [
                LowLevelFilth(placeholder="IPv4", regex=ip_regex, **kwargs),
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

        size = 20000
        for i in range(0, len(cmds), size):
            chunk = cmds[i:i + size]
            cmd = "sed -i '{}' {}".format(" ; ".join(chunk), abs_file)
            _ = utils.run_local_cmd(cmd=cmd, log_output=False, log_input=False)
        return abs_file

    def iter_filth(self, src_file):
        assert self.low_level_filths
        for filths in self.low_level_filths:
            for filth in filths:
                grep_cmd = f'grep -Eo "{filth.regex}" {src_file} | uniq | sort -g'
                res = utils.run_local_cmd(grep_cmd, log_output=False, log_input=True)
                segments = set(seg for seg in res.stdout.split("\n") if seg)
                segments = set(self.clean_suffix(seg, "'") for seg in segments)
                yield filth, sorted(segments, key=lambda x: -len(x))
        raise StopIteration

    def filter_raw_files(self, raw_files):
        excluded_files = set()
        for src_file in raw_files:
            filth_to_segment = defaultdict(list)
            for filth, segments in self.iter_filth(src_file):
                filth_to_segment[filth] += segments
                if len(filth_to_segment[filth]) > self.threshold:
                    utils.logger.info(f"LowLevel: Exclude {src_file}: {len(filth_to_segment[filth])}")
                    excluded_files.add(src_file)
            else:
                self.file_to_filth_segment[src_file] = dict(filth_to_segment)

        self.raw_files = set(self.file_to_filth_segment.keys()) - excluded_files
