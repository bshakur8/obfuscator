import os
import platform
from collections import defaultdict
from functools import lru_cache

from ..lib.exceptions import NoTextFilesFoundError
from ..lib.detectors import CredentialFilth, FilesDirFilth
from ..lib import utils
from .abs_file_splitter import FileSplitters
from ..lib.enums import SegmentsEnum

SED_SEPARATOR = "@"
SED_FORBIDDEN_CHARS = f"[]*^{SED_SEPARATOR}"


class ObfuscateLowLevel(FileSplitters):
    def __init__(self, args, name: str = "LowLevel"):
        super().__init__(args, name)
        self.low_level_filths = []
        self.file_to_filth_segment = {}
        self.threshold = args.threshold
        self._log_kwargs = {"log_output": self.args.debug, "log_input": self.args.debug}

    @staticmethod
    def clean_suffix(string, chars):
        return string.rstrip(chars).strip()

    def pre_all(self):
        super().pre_all()
        ipv4_regex = r"(25[0-5]|2[0-4][0-9]|[0-1]?[0-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|[0-1]?[0-9]?[0-9])){3}"
        ipv6_regex = r"(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))"
        file_regex = FilesDirFilth.regex_str
        credentials_regex = CredentialFilth.regex_str
        mac_addr_regex = r"([a-f0-9A-F]{2}:){5}[a-f0-9A-F]{2}"

        kwargs = {"salt": self.args.salt}

        # Order is important! ip can be inside a file dir but not vise-versa
        self.low_level_filths = [
            [
                LowLevelFilth(placeholder=SegmentsEnum.FILE_DIR.value, regex=file_regex, **kwargs),
                LowLevelFilth(placeholder=SegmentsEnum.CREDENTIALS.value, regex=credentials_regex, **kwargs),
                LowLevelFilth(placeholder=SegmentsEnum.MAC_ADDR.value, regex=mac_addr_regex, **kwargs),
            ],
            [
                LowLevelFilth(placeholder=SegmentsEnum.IP.value, regex=ipv4_regex, **kwargs),
                LowLevelFilth(placeholder=SegmentsEnum.IPv6.value, regex=ipv6_regex, **kwargs),
            ],
        ]

    def pre_one(self, src_file):
        src_file, _, filth_to_segment = self.orchestrate_iterator(src_file, check_with_threshold=False)
        self.file_to_filth_segment[src_file] = filth_to_segment
        return [src_file]

    def obfuscate_one(self, *args, **__):
        abs_file, filth_to_segment = args[0]
        self._print(abs_file)
        filth_to_segment = filth_to_segment or self.file_to_filth_segment[abs_file]
        cmds = []
        for filth, segments in filth_to_segment.items():
            for segment in segments:
                obf_segment = filth.replace_with(segment)
                for t in SED_FORBIDDEN_CHARS:
                    segment = segment.replace(t, rf"\{t}")
                cmds.append(f"s{SED_SEPARATOR}{segment}{SED_SEPARATOR}{obf_segment}{SED_SEPARATOR}g")
        # Cannot run in parallel: will have missing obfuscated segments
        for chunk in utils.chunkify(cmds, size=min(50, int(self.args.threshold / 5))):
            cmd = f"""{self.args.replacer} '{" ; ".join(chunk)}' {abs_file}"""
            utils.run_local_cmd(cmd=cmd, **self._log_kwargs)
        return abs_file

    def orchestrate_iterator(self, src_file, *_, check_with_threshold=True, **__):
        if not self.low_level_filths:
            raise AssertionError()
        grep = f'{self.args.searcher} "{{r}}" {src_file} | {self.args.sorter}'

        filth_to_segment = defaultdict(list)
        total_segments = 0
        for filths in self.low_level_filths:
            for filth in filths:
                res = utils.run_local_cmd(grep.format(r=filth.regex), **self._log_kwargs)
                segments = set(s for s in res.stdout.split("\n") if s)
                total_segments += len(segments)
                filth_to_segment[filth] += segments

                if check_with_threshold and total_segments >= self.threshold:
                    utils.logger.info(f"LowLevel: Exclude {src_file}: {total_segments} segments")
                    return src_file, False, {}

        # Finished all checks - we can return True
        if total_segments:
            utils.logger.info(f"LowLevel: Include {src_file}: {total_segments} segments")
            for filth, segments in filth_to_segment.items():
                segments = sorted(set(self.clean_suffix(seg, "'") for seg in segments), key=lambda x: -len(x))
                filth_to_segment[filth] = segments

            return src_file, True, dict(filth_to_segment)

        # No segments - no need to handle
        return src_file, None, {}


class ObfuscateUsingRipGrep(ObfuscateLowLevel):
    """Obfuscate all files in place but not giving them IDs:

    - No files splits
    - Suitable for small files and low CPU and memory resources
    """

    def __init__(self, args, name: str = "RipGrep"):
        super().__init__(args, name=name)

    @property
    @lru_cache(1)
    def ripgrep(self):
        _platform = platform.platform().lower()
        bin_path = self.args.ripgrep_path if self.args.ripgrep_path else "./"
        if "ubuntu" in _platform:
            return os.path.join(bin_path, "rg_ubuntu.bin")
        if "centos" in _platform:
            if "aarch64" in _platform:
                return os.path.join(bin_path, "rg_centos_aarch64.bin")
            if "x86_64" in _platform:
                return os.path.join(bin_path, "rg_centos_x86_64.bin")
        raise OSError(f"Unsupported OS: {_platform}")

    def pre_one(self, src_file):
        return [src_file]

    def obfuscate(self):
        """Obfuscate input files

        If there's only one worker or one file: Run in single process without multiprocessing Pool
        """
        if not self.raw_files:
            raise NoTextFilesFoundError(f"{self} No files to obfuscate")

        with self.pool_function(self.args.workers) as pool:
            pool.map(self.obfuscate_one, self.raw_files)

    def obfuscate_one(self, *args, **kwargs):
        src_file = args[0]
        dirname = os.path.dirname(src_file)
        self._print(src_file)
        # local rg
        replace_cmd = (
            f'{self.ripgrep} --passthru -ie "{{r}}" --replace {{p}} {src_file} '
            f"2>&1 | sudo tee {{t}} > /dev/null && sudo mv {{t}} {src_file}"
        )

        for filths in self.low_level_filths:
            for filth in filths:
                utils.logger.debug(f"Obfuscate {filth.placeholder} segments of '{src_file}'")
                tmp_file = os.path.join(dirname, f"{src_file}__{filth.placeholder.lower().replace('-', '_')}.tmp")
                cmd = replace_cmd.format(r=filth.regex, p="{{" + filth.placeholder, t=tmp_file)
                utils.run_local_cmd(cmd=cmd, **self._log_kwargs)
                utils.logger.debug(f"Done obfuscate {filth.placeholder}: '{src_file}'")

        return src_file


class LowLevelFilth:
    def __init__(self, salt: str, placeholder: str, regex: str):
        self.salt = salt
        self.placeholder = placeholder
        self.regex = regex
        self._const_hash = utils.hash_string("".join((str(x) for x in (self.placeholder, self.salt))))

    def __str__(self):
        return self.placeholder

    def __repr__(self):
        return self.__str__()

    def replace_with(self, text):
        return "{{" + "%s-%s" % (self.placeholder, utils.hash_string(f"{self._const_hash}{text}")) + "}}"
