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

    def _obfuscate_one(self, abs_file, **kwargs):
        cmds = []
        for filth, segments in self.iter_filth(abs_file):
            for segment in segments:
                obf_segment = filth.replace_with(segment)
                for t in "[]":
                    segment = segment.replace(t, fr'\{t}')
                cmds.append(f's@{segment}@{obf_segment}@g')

        size = 2000
        for i in range(0, len(cmds), size):
            chunk = cmds[i:i + size]
            cmd = "sed -i '{}' {}".format(" ; ".join(chunk), abs_file)
            _ = utils.run_local_cmd(cmd=cmd, log_output=False, log_input=False)
        return abs_file

    def iter_filth(self, src_file):
        for filths in self.low_level_filths:
            for filth in filths:
                # grep -Eo "([0-9]{1,3}[\.]){3}[0-9]{1,3}" var_log_secure.txt | sort --unique
                # grep -Eo "(/[^ *\^\"']+)+" /tmp/test/files/var_log_secure.txt | uniq | sort -g | uniq
                grep_cmd = f'grep -Eo "{filth.regex}" {src_file} | uniq | sort -g | uniq'
                res = utils.run_local_cmd(grep_cmd, log_output=True, log_input=True)
                # segments = set(seg.replace("'", '').replace('"', '').strip() for seg in res.stdout.split("\n") if seg)
                segments = set(self.clean_suffix(seg, "'") for seg in res.stdout.split("\n") if seg)
                yield filth, sorted(segments, key=lambda x: -len(x))

        raise StopIteration
