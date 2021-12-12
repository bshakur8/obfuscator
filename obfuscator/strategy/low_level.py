import os
import platform
from collections import defaultdict
from functools import lru_cache

from obfuscator.detectors.detectors import (
    LowLevelFilth,
    MyCredentialFilth,
    IPv4Filth,
    MACFilth,
    FilesDirFilth,
)
from obfuscator.strategy import utils
from obfuscator.strategy.utils import info, debug
from obfuscator.strategy.base_spliter import BaseFileSplitters
from obfuscator.strategy.enums import Segments
from obfuscator.strategy.exceptions import NoTextFilesFound


SED_SEPARATOR = "@"
SED_FORBIDDEN_CHARS = "[]*^" + SED_SEPARATOR


class ObfuscateLowLevel(BaseFileSplitters):
    NAME = "LowLevel"

    def __init__(self, args):
        super().__init__(args)
        self.low_level_filths = []
        self.file_to_filth_segment = {}
        self.threshold = args.threshold

    @staticmethod
    def clean_suffix(string, chars):
        return string.rstrip(chars).strip()

    def pre_all(self):
        super().pre_all()
        kwargs = {"salt": self.args.salt}

        # Order is important! ip can be inside a file dir but not vise-versa
        self.low_level_filths = [
            [
                LowLevelFilth(
                    placeholder=Segments.FILE_DIR.value,
                    regex=FilesDirFilth.REGEX,
                    **kwargs,
                ),
                LowLevelFilth(
                    placeholder=Segments.CREDENTIALS.value,
                    regex=MyCredentialFilth.REGEX,
                    **kwargs,
                ),
                LowLevelFilth(placeholder=Segments.MAC_ADDR.value, regex=MACFilth.REGEX, **kwargs),
            ],
            [
                LowLevelFilth(placeholder=Segments.IP.value, regex=IPv4Filth.REGEX_2, **kwargs),
            ],
        ]

    def pre_one(self, src_file):
        src_file, _, filth_to_segment = self.orchestrate_iterator(src_file, check_with_threshold=False)
        self.file_to_filth_segment[src_file] = filth_to_segment
        return [src_file]

    def obfuscate_one(self, *args, **kwargs):
        abs_file, filth_to_segment = args[0]
        self._print(abs_file)
        filth_to_segment = filth_to_segment or self.file_to_filth_segment[abs_file]
        cmds = []
        for filth, segments in filth_to_segment.items():
            for segment in segments:
                obf_segment = filth.replace_with(segment)
                for t in SED_FORBIDDEN_CHARS:
                    segment = segment.replace(t, fr"\{t}")
                cmds.append(f"s{SED_SEPARATOR}{segment}{SED_SEPARATOR}{obf_segment}{SED_SEPARATOR}g")

        # Cannot run in parallel: will have missing obfuscated segments
        for chunk in utils.chunkify(cmds, size=min(50, int(self.args.threshold / 5))):
            cmd = "{} '{}' {}".format(self.args.replacer, " ; ".join(chunk), abs_file)
            _ = utils.run_local_cmd(cmd=cmd, **self._log_kwargs)

        return abs_file

    def orchestrate_iterator(self, src_file, *args, check_with_threshold=True, **kwargs):
        assert self.low_level_filths
        grep = f'{self.args.searcher} "{{r}}" {src_file} | {self.args.sorter}'

        filth_to_segment = defaultdict(list)
        total_segments = 0
        for filths in self.low_level_filths:
            for filth in filths:
                res = utils.run_local_cmd(grep.format(r=filth.regex), **self._log_kwargs)
                if res.stderr:
                    raise OSError(res.stderr)
                segments = set(s for s in res.stdout.split("\n") if s)
                total_segments += len(segments)
                filth_to_segment[filth] += segments

                if check_with_threshold and total_segments >= self.threshold:
                    info(f"{self}: Exclude {src_file}: {total_segments} segments")
                    return src_file, False, {}

        # Finished all checks - we can return True
        if total_segments:
            info(f"{self}: Include {src_file}: {total_segments} segments")
            for filth, segments in filth_to_segment.items():
                segments = sorted(
                    set(self.clean_suffix(seg, "'") for seg in segments),
                    key=lambda x: -len(x),
                )
                filth_to_segment[filth] = segments

            return src_file, True, dict(filth_to_segment)

        # No segments - no need to handle
        return src_file, None, {}


class ObfuscateUsingRipGrep(ObfuscateLowLevel):
    """
    Obfuscate all files in place but not giving them IDs:
     - No files splits
     - Suitable for small files and low CPU and memory resources
    """

    NAME = "RipGrep"

    @property
    @lru_cache(1)
    def ripgrep(self):
        if self.args.ripgrep_path:
            return self.args.ripgrep_path
        _platform = platform.platform().lower()
        if "ubuntu" in _platform:
            return "./rg_ubuntu"
        if "centos" in _platform:
            return "./rg_centos"
        raise OSError("Unsupported OS")

    def pre_one(self, src_file):
        return [src_file]

    def obfuscate(self):
        """Obfuscate input files:
        - If there's only one workers or one file: Run in single process without multiprocessing Pool
        """
        if not self.raw_files:
            raise NoTextFilesFound(f"{self.__str__()} No files to obfuscate")

        with self.pool_function(self.args.workers) as pool:
            pool.map(self.obfuscate_one, self.raw_files)

    def obfuscate_one(self, *args, **kwargs):
        src_file = args[0]
        dirname = os.path.dirname(src_file)
        self._print(src_file)
        # local rg
        replace_cmd = (
            f'{self.ripgrep} --passthru -ie "{{r}}" --replace {{p}} {src_file} '
            f"2>&1 | tee {{t}} > /dev/null && mv {{t}} {src_file}"
        )

        for filths in self.low_level_filths:
            for filth in filths:
                debug(f"Obfuscate {filth.placeholder} segments of '{src_file}'")
                tmp_file = os.path.join(
                    dirname,
                    f"{src_file}__{filth.placeholder.lower().replace('-', '_')}.tmp",
                )
                cmd = replace_cmd.format(r=filth.regex, p="{{" + filth.placeholder, t=tmp_file)
                utils.run_local_cmd(cmd=cmd, **self._log_kwargs)
                debug(f"Done obfuscate {filth.placeholder}: '{src_file}'")

        return src_file
