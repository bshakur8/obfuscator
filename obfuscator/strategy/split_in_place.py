#!/usr/bin/env python3
from strategy import utils
from strategy.abs_file_splitter import FileSplitters
from strategy.split_and_merge import ObfuscateSplitAndMerge


class ObfuscateSplitInPlace(ObfuscateSplitAndMerge):
    """
    Split big files and obfuscate them in place
     - Small files are obfuscated in-place
     - Suitable for small-big files with limited disk space
    """

    def __init__(self, args, name=None):
        super().__init__(args=args, name=name or "SplitInPlace")
        self.sort_func = utils.sort_func

    def obfuscate_one(self, *args, **kwargs):
        """
        Worker function: Takes a filename and obfuscate it inplace
        """
        (abs_file, _) = args[0]
        self._print(abs_file)
        return utils.obfuscate_in_place(abs_file, scrubber=self.scrubber)


class ObfuscateInplace(ObfuscateSplitInPlace):
    """
    Obfuscate all files in place:
     - No files splits
     - Suitable for small files. Big files becomes bottleneck
    """

    def __init__(self, args, name=None):
        super().__init__(args, name=name or "InPlace")
        self.num_parts = 1  # No splits

    def pre_all(self):
        self.customise_scrubber()
        return FileSplitters.pre_all(self)

    def pre_one(self, src_file):
        return [src_file]

    def post_one(self, pool, obfuscated_files, *args, **kwargs):
        pass
