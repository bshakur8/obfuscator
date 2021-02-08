from detectors.detectors import LowLevelFilth, ObfuscatorLookup, MyCredentialFilth
from strategy import utils
from strategy.abs_file_splitter import FileSplitters


class ObfuscateLowLevel(FileSplitters):
    def __init__(self, args, name=None):
        super().__init__(args, name or "LowLevel")
        self.low_level_filths = []

    def pre_all(self):
        super().pre_all()
        pool_lookup_table = self.pool_function().lookup_table
        lookup_table = ObfuscatorLookup(collection=pool_lookup_table)

        ip_regex = r"([0-9]{1,3}[\.]){3}[0-9]{1,3}"
        file_regex = r"(/[^/ ]*)+/?"
        credentials_regex = MyCredentialFilth.regex_str
        mac_addr_regex = r"[0-9a-f]\{12\}'"

        kwargs = {'salt': self.args.salt, 'lookup': lookup_table}

        # Order is important!
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

    def _obfuscate_one(self, abs_file, **kwargs):
        cmds = []
        for filth, segments in self.iter_filth(abs_file):
            for segment in segments:
                obf_segment = filth.replace_with(segment)
                sed_cmd = f"s/{segment}/{obf_segment}/g"
                cmds.append(sed_cmd)
                if len(cmds) > 1000:
                    cmd = "sed -i '{}' {}".format(" ; ".join(cmds), abs_file)
                    _ = utils.run_local_cmd(cmd=cmd, log_output=False, log_input=True)
                    cmds = []

        cmd = "sed -i '{}' {}".format(" ; ".join(cmds), abs_file)
        _ = utils.run_local_cmd(cmd=cmd)
        return abs_file

    def iter_filth(self, src_file):
        for filths in self.low_level_filths:
            for filth in filths:
                # grep -Eo "([0-9]{1,3}[\.]){3}[0-9]{1,3}" var_log_secure.txt | sort --unique
                grep_cmd = f'grep -Eo "{filth.regex}" {src_file} | sort --unique'
                res = utils.run_local_cmd(grep_cmd, log_output=False, log_input=True)

                segments = set(seg.replace("'", '').replace('"', '') for seg in res.stdout.split("\n") if seg)
                segments = set(seg.replace('/', '\\/') for seg in segments if seg)
                yield filth, segments

        raise StopIteration
