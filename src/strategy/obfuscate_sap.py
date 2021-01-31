#!/usr/bin/env python3
import utils
from strategy.abs_file_splitter import FileSplitters
from strategy.obfuscate_sam import ObfuscateSplitAndMerge


class ObfuscateSplitInPlace(ObfuscateSplitAndMerge):

    def __init__(self, args, name=None):
        super().__init__(args=args, name=name or "SplitInPlace")

    def pre(self):
        FileSplitters.pre(self)

    def post(self):
        FileSplitters.post(self)

    def _obfuscate_worker(self, src_file):
        """
        Worker function: Takes a filename and obfuscate it
         - Opens a new temp file to write obfuscated line to it
         - Copy temp file to a new file with same name in target dir
        :param src_file: Filename to obfuscate
        """
        utils.logger.info(f"Obfuscate '{src_file}'")
        return utils.obfuscate_in_place(src_file, scrubber=self._scrubber)

    def _prepare_merge_files(self, obfuscated_files, **kwargs):
        src_file = kwargs.pop('src_file')
        return {src_file: obfuscated_files}
