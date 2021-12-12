#!/usr/bin/env python3
import os
import shutil
import traceback
from collections import defaultdict
from datetime import datetime
from functools import partial
from io import DEFAULT_BUFFER_SIZE
from tempfile import mkstemp

from obfuscator.detectors.detectors import ObfuscatorDetectors
from obfuscator.detectors.scrubber import ObfuscatorScrubber
from obfuscator.strategy import utils
from obfuscator.strategy.base_spliter import BaseFileSplitters
from obfuscator.strategy.exceptions import NoTextFilesFound
from obfuscator.strategy.utils import debug, error, exception, info


def sort(name, index):
    """Sort function by index
    :param name: File name to sort
    :param index: Index to take
    """
    try:
        return int(name.split(utils.FILE_PREFIX)[index])
    except (IndexError, ValueError):
        return 0


class ObfuscateSplitAndMerge(BaseFileSplitters):
    """
    Split big files and obfuscate them, and merge temp files
     - Suitable for big files with no limited disk space
    """

    NAME = "Split&Merge"

    def __init__(self, args):
        super().__init__(args=args)
        # Folder to save file splits in
        self.scrubber = None
        self._tmp_folder = None
        self.num_parts = self.args.workers

    @staticmethod
    def sort_func(item):
        return sort(item, -3)

    def pre_all(self):
        super().pre_all()
        self.customise_scrubber()
        # Create temp folder: save file splits and removed at the end
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")  # obf_tmp_20200809_102729
        self._tmp_folder = os.path.join(self.args.output_folder, f"{utils.TMP_FOLDER_PREFIX}{ts}")
        debug(f"Create splits temp folder: {self._tmp_folder}")
        utils.create_folder(self._tmp_folder)

    def customise_scrubber(self):
        if self.scrubber:
            return
        scrubber = ObfuscatorScrubber()

        for detector in ObfuscatorDetectors:
            detector.filth_cls.salt = self.args.salt
            debug(f"Add Detector: {detector}")
            scrubber.add_detector(detector)

        self.scrubber = scrubber

    def post_all(self):
        """
        Post operations:
         - Remove temporary folder
        """
        if self._tmp_folder:
            debug(f"Remove temp folder: {self._tmp_folder}")
            try:
                shutil.rmtree(self._tmp_folder)
            except OSError as e:
                error(f"Error: {e.filename} - {e.strerror}.")

    def pre_one(self, src_file):
        return utils.get_extended_file(
            filename=src_file,
            size_limit=self.args.min_split_size_in_bytes,
            num_parts=self.num_parts,
            output_folder=self._tmp_folder,
            debug=self.args.debug,
        )

    def post_one(self, pool, obfuscated_files, *args, **kwargs):
        files_to_merge = self._prepare_merge_files(obfuscated_files=obfuscated_files)
        if files_to_merge:
            pool.map(self._merge, files_to_merge.items())

    def obfuscate_one(self, *args, **kwargs):
        """
        Worker function: Takes a filename and obfuscate it
         - Opens a new temp file to write obfuscated line to it
         - Copy temp file to a new file with same name in target dir
        """
        abs_file = utils.itemgetter(args, 0, type_needed=str)
        self._print(abs_file)

        # Create temp file, return fs and abs_tmp_path
        prefix = f"{os.path.basename(abs_file)}{utils.FILE_PREFIX}"
        new_folder_name = utils.get_folders_difference(filename=abs_file, folder=self._tmp_folder)
        obf_mkstemp = partial(mkstemp, dir=new_folder_name, text=True, prefix=prefix)
        tmp_fd, abs_tmp_path = obf_mkstemp(suffix=utils.NEW_FILE_SUFFIX)
        line_idx = 0
        try:
            with open(tmp_fd, "w", buffering=DEFAULT_BUFFER_SIZE) as writer, open(
                abs_file, "r", buffering=DEFAULT_BUFFER_SIZE, encoding="utf-8"
            ) as reader:
                for line_idx, line in enumerate(reader):
                    # clean file and write to new_logs file
                    writer.write(self.scrubber.clean(text=line))

        except (Exception,):
            exception(f"Exception in {self.__class__.__name__}")
            # remove failed temp file
            utils.remove_files([abs_tmp_path])

            # In case of exception, we create another file - we use another temp file
            # and write the traceback inside
            format_exception = traceback.format_exc().strip()
            err_tmp_fd, abs_tmp_path = obf_mkstemp(suffix=".err.tmp")

            with open(err_tmp_fd, "w") as writer:
                line = f"Line {line_idx}: " if line_idx else ""
                writer.write(f"{line}{format_exception}")

        finally:
            if utils.PART_SUFFIX in abs_file:
                debug("Remove file: {}".format(abs_file))
                utils.remove_files([abs_file])
                debug("Done remove file: {}".format(abs_file))

        info(f"Done obfuscate '{abs_file}'")
        return abs_tmp_path

    def _prepare_merge_files(self, obfuscated_files):
        """
        Merge all file splits into one new obfuscated file.
        Get all file parts, sort them by index, merge them one-by-one into a new file.
        Delete
        """
        if not obfuscated_files:
            raise NoTextFilesFound("No files to merge!")

        obfuscated_files = list(obfuscated_files)
        dict_files = defaultdict(list)

        if len(obfuscated_files) == 1:
            # move to output_folder
            obfuscated_abs_path = obfuscated_files[0]
            orig_basename = os.path.basename(obfuscated_abs_path).partition(utils.FILE_PREFIX)[0]
            target_dir = os.path.dirname(obfuscated_abs_path.replace(self._tmp_folder, ""))
            target_dir = self.args.output_folder + target_dir.strip("/")
            utils.create_folder(target_dir)
            shutil.move(obfuscated_abs_path, os.path.join(target_dir, orig_basename))
        else:
            # Sort parts by initial index to merge them by order
            obfuscated_files = sorted(obfuscated_files, key=self.sort_func)

            for obfuscated_abs_path in obfuscated_files:
                orig_basename = os.path.basename(obfuscated_abs_path).partition(utils.FILE_PREFIX)[0]
                target_dir = os.path.dirname(obfuscated_abs_path.replace(self._tmp_folder, ""))
                target_dir = self.args.output_folder + target_dir
                utils.create_folder(target_dir)
                target_file = os.path.join(target_dir, orig_basename)
                dict_files[target_file].append(obfuscated_abs_path)

        return dict_files

    @staticmethod
    def _merge(one_tuple):
        """
        Merge function
        :param one_tuple: Tuple, list files to merge into output file
        """
        output_file, list_files = one_tuple
        debug(f"Merge {output_file}")
        utils.combine_files(files=list_files, output_file=output_file)
