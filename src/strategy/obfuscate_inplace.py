#!/usr/bin/env python3
import os
from shutil import copyfile

import utils
from strategy.abs_file_splitter import FileSplitters


class ObfuscateInplace(FileSplitters):

    def __init__(self, args, name=None):
        super().__init__(args, name=name or "InPlace")
        self.set_default_scrubber()

    def pre(self):
        super().pre()

        # Copy files to obfuscate to output_folder - since they will undergo obfuscation in-place
        if os.path.commonprefix([self.args.output_folder, self.args.input_folder]) != self.args.output_folder:
            utils.logger.debug(f"Copy files to: {self.args.output_folder} for inplace obfuscation")
            new_files = []
            for f in self.raw_files:
                new = os.path.join(self.args.output_folder, os.path.basename(f))
                copyfile(f, new)
                if self.args.remove_original:
                    utils.remove_files([f])
                new_files.append(new)
            # Work with new list
            self.raw_files = new_files

    def obfuscate(self):
        utils.logger.info(f"Obfuscate Inplace all files")
        if self.args.debug and self.args.workers == 1 or len(self.raw_files) == 1:
            for f in self.raw_files:
                self._obfuscate_worker(src_file=f)
        else:
            with self.pool_function(self.args.workers) as pool:
                pool.map(self._obfuscate_worker, self.raw_files)

    def _obfuscate_worker(self, src_file):
        return utils.obfuscate_in_place(src_file, scrubber=self._scrubber)
