#!/usr/bin/env python3
from strategy import utils
from strategy.abs_file_splitter import FileSplitters


class ObfuscateInplace(FileSplitters):

    def __init__(self, args, name=None):
        super().__init__(args, name=name or "InPlace")
        self.set_default_scrubber()

    def pre(self):
        super().pre()
        self.raw_files = utils.clone_folder(raw_files=self.raw_files, args=self.args)

    def obfuscate(self):
        utils.logger.info(f"Obfuscate Inplace all files")
        if (self.args.debug and self.args.workers == 1) or len(self.raw_files) == 1:
            for f in self.raw_files:
                self._obfuscate_worker(src_file=f)
        else:
            with self.pool_function(self.args.workers) as pool:
                pool.map(self._obfuscate_worker, self.raw_files)

    def _obfuscate_worker(self, src_file):
        return utils.obfuscate_in_place(src_file, scrubber=self._scrubber, args=self.args)
