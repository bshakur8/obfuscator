from detectors.detectors import LowLevelFilth, MyCredentialFilth
from strategy import utils
from strategy.abs_file_splitter import FileSplitters


class ObfuscateLowLevel(FileSplitters):
    def __init__(self, args, name=None):
        super().__init__(args, name or "LowLevel")
        self.low_level_filths = []

    def clean_suffix(self, string, chars):
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
        for filth, segments in self.iter_filth(abs_file):
            for segment in segments:
                obf_segment = filth.replace_with(segment)
                for t in "[]":
                    segment = segment.replace(t, fr'\{t}')
                cmds.append(f's@{segment}@{obf_segment}@g')

        size = 20000
        for i in range(0, len(cmds), size):
            chunk = cmds[i:i + size]
            cmd = "sed -i '{}' {}".format(" ; ".join(chunk), abs_file)
            _ = utils.run_local_cmd(cmd=cmd, log_output=False, log_input=False)
        return abs_file

    def iter_filth(self, src_file, sort=True, clean=True, threshold=None):
        for filths in self.low_level_filths:
            for filth in filths:
                grep_cmd = f'grep -Eo "{filth.regex}" {src_file} | uniq'
                if sort:
                    grep_cmd += " | sort -g | uniq"

                res = utils.run_local_cmd(grep_cmd, log_output=False, log_input=True)
                segments = set(seg for seg in res.stdout.split("\n") if seg)
                if clean:
                    segments = set(self.clean_suffix(seg, "'") for seg in segments)
                if sort:
                    segments = sorted(segments, key=lambda x: -len(x))
                if threshold and threshold > len(segments):
                    utils.logger.info(f"number of segments in {src_file} = {len(segments)}")
                    yield None
                yield filth, segments

        raise StopIteration

    def can_run(self, src_file, threshold=100):
        return next(self.iter_filth(src_file, sort=False, clean=False, threshold=threshold)) is None
