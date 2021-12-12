#!/usr/bin/env python3
from io import DEFAULT_BUFFER_SIZE

import in_place

from obfuscator.strategy.base_spliter import BaseFileSplitters
from obfuscator.strategy.split_and_merge import ObfuscateSplitAndMerge, sort


def obfuscate_in_place(src_file, scrubber):
    # Create temp file, return fs and abs_tmp_path
    with in_place.InPlace(name=src_file, buffering=DEFAULT_BUFFER_SIZE) as fd:
        for line in fd:
            fd.write(scrubber.clean(text=line))
    return src_file


class ObfuscateSplitInPlace(ObfuscateSplitAndMerge):
    """Split big files and obfuscate them in place
    - Small files are obfuscated in-place
    - Suitable for small-big files with limited disk space
    """

    NAME = "SplitInPlace"

    def __init__(self, args):
        super().__init__(args=args)

    def obfuscate_one(self, *args, **kwargs):
        """
        Worker function: Takes a filename and obfuscate it inplace
        """
        (abs_file, _) = args[0]
        self._print(abs_file)
        return obfuscate_in_place(abs_file, scrubber=self.scrubber)


class ObfuscateInplace(ObfuscateSplitInPlace):
    """Obfuscate all files in place:
    - No files splits: no extra storage overhead
    - Suitable for small files. Big files becomes a bottleneck
    """

    NAME = "InPlace"

    def __init__(self, args):
        super().__init__(args)
        self.num_parts = 1  # No splits

        # Set the output folder to be the input folder
        self.args.output_folder = self.args.input_folder

    @staticmethod
    def sort_func(item):
        return sort(item, -1)

    def pre_all(self):
        self.customise_scrubber()
        return BaseFileSplitters.pre_all(self)

    def pre_one(self, src_file):
        return [src_file]

    def post_one(self, pool, obfuscated_files, *args, **kwargs):
        pass
