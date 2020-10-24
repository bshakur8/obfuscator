#!/usr/bin/env python3
import fileinput
import os
import sys
import traceback
from shutil import copyfile

from .abs_file_splitter import FileSplitters
from .. import utils


class ObfuscateInplace(FileSplitters):

    def __init__(self, args):
        super().__init__(args, name="InPlace")
        self.set_default_scrubber()

    def _pre(self):
        super()._pre()
        self.list_files = self._get_txt_files()

        # Copy files to obfuscate to output_folder - since they will undergo obfuscation in-place
        # If output_folder == input_folder\file_folder
        if os.path.commonprefix([self.args.output_folder, self.args.input_folder]) != self.args.output_folder:
            utils.logger.debug(f"Copy files to: {self.args.output_folder} for inplace obfuscation")
            new_files = []
            for f in self.list_files:
                new = os.path.join(self.args.output_folder, os.path.basename(f))
                copyfile(f, new)
                new_files.append(new)

            # Work with new list
            self.list_files = new_files

    def _obfuscate(self):
        assert self.list_files, "no files to obfuscate"

        utils.logger.info(f"Obfuscate Inplace all files")

        lines = []
        with fileinput.input(files=self.list_files, inplace=True) as fd:
            for line_idx, line in enumerate(fd):
                # in place
                try:
                    lines.append(self._scrubber.clean(text=line))
                except Exception:
                    lines.append(f"Line {line_idx}: {traceback.format_exc().strip()}")

                if len(lines) > self.BUFFER_SIZE:
                    sys.stdout.writelines(lines)
                    lines = []

            sys.stdout.writelines(lines)
