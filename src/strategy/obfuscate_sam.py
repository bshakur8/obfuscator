#!/usr/bin/env python3
import os
import shutil
import traceback
from collections import defaultdict
from datetime import datetime
from functools import partial
from tempfile import mkstemp

from .abs_file_splitter import FileSplitters
from .. import utils
from ..utils import TMP_FOLDER_PREFIX


class ObfuscateSplitAndMerge(FileSplitters):

    def __init__(self, args):
        super().__init__(args=args, name="Split&Merge")

        # Folder to save file splits in
        self._files_tmp_folder = None

        self.set_default_scrubber()

    def _pre(self):
        super()._pre()
        self.list_raw_files = self._prepare_file_splits()

    def _post(self):
        """
        Post operations:
         - Remove temporary folder
        """
        if self._files_tmp_folder:
            utils.logger.debug(f"Remove temp folder: {self._files_tmp_folder}")
            try:
                shutil.rmtree(self._files_tmp_folder)
            except OSError as e:
                utils.logger.error(f"Error: {e.filename} - {e.strerror}.")

    def _prepare_file_splits(self):
        """Prepare output and temporary folders before start"""
        utils.logger.debug("Create splits temp folder")
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        # format: obf_tmp_20200809_102729
        self._files_tmp_folder = os.path.join(self.args.output_folder, f"{TMP_FOLDER_PREFIX}{ts}")
        # Create temp folder: save file splits and removed at the end
        utils.create_folder(self._files_tmp_folder)

        utils.logger.debug("Get text files to obfuscate")
        list_txt_files = self._get_txt_files()
        if not list_txt_files:
            utils.logger.warning(f"Folder '{self.args.input_folder}' has no text files")
        return list_txt_files

    def _obfuscate(self):
        """Obfuscate input files:
         - If there's only one workers or one file: Run in single process without multiprocessing Pool
        """
        if not self.list_raw_files:
            raise utils.NoTextFilesFound(f"No files to obfuscate")

        with self.pool_function(self.args.workers) as pool:
            for src_file in self.list_raw_files:
                list_extended_files = utils.get_extended_file(filename=src_file,
                                                              size_limit=self.args.min_split_size_in_bytes,
                                                              num_parts=self.args.workers,
                                                              output_folder=self._files_tmp_folder)
                list_obfuscated_files = []
                # If 1 worker or one file to handle: run single process
                if self.args.debug and self.args.workers == 1 or len(list_extended_files) == 1:
                    for f in list_extended_files:
                        list_obfuscated_files.append(self._obfuscate_worker(src_file=f))
                else:
                    list_obfuscated_files = pool.map(self._obfuscate_worker, list_extended_files)

                files_to_merge = self._prepare_merge_files(list_obfuscated_files=list_obfuscated_files)

                if files_to_merge:
                    if self.args.debug and len(files_to_merge) == 1:
                        self._merge(tuple(files_to_merge.items())[0])
                    else:
                        pool.map(self._merge, files_to_merge.items())
                utils.logger.debug(f"Done merge '{src_file}'")

    def _obfuscate_worker(self, src_file):
        """
        Worker function: Takes a filename and obfuscate it
         - Opens a new temp file to write obfuscated line to it
         - Copy temp file to a new file with same name in target dir
        :param src_file: Filename to obfuscate
        """
        # Create temp file, return fs and abs_tmp_path
        utils.logger.info(f"Obfuscate '{src_file}'")

        prefix = f"{os.path.basename(src_file)}{utils.FILE_PREFIX}"
        new_folder_name = utils.get_folders_difference(filename=src_file, folder=self._files_tmp_folder)

        obf_mkstemp = partial(mkstemp, dir=new_folder_name, text=True, prefix=prefix)

        tmp_fd, abs_tmp_path = obf_mkstemp(suffix=utils.NEW_FILE_SUFFIX)
        line_idx = 0
        try:
            with open(tmp_fd, 'w', buffering=self.BUFFER_SIZE) as writer,\
                    open(src_file, 'r', buffering=self.BUFFER_SIZE, encoding="utf-8") as reader:
                for line_idx, line in enumerate(reader):
                    # clean file and write to new_logs file
                    writer.write(self._scrubber.clean(text=line))

        except Exception as e:
            utils.logger.error(f"Exception in obfuscate_sam._obfuscate_worker : {str(e)}")
            # remove failed temp file
            utils.remove_files([abs_tmp_path])

            # In case of exception, we create another file - we use another temp file
            # and write the traceback inside
            format_exception = traceback.format_exc().strip()
            err_tmp_fd, abs_tmp_path = obf_mkstemp(suffix=".err.tmp")

            with open(err_tmp_fd, 'w') as writer:
                line = f"Line {line_idx}: " if line_idx else ''
                writer.write(f"{line}{format_exception}")

        finally:
            if self.args.remove_original or utils.PART_SUFFIX in src_file:
                utils.logger.debug("Remove file: {}".format(src_file))
                utils.remove_files([src_file])
                utils.logger.debug("Done remove file: {}".format(src_file))

        utils.logger.info(f"Done obfuscate '{src_file}'")
        return abs_tmp_path

    def _prepare_merge_files(self, list_obfuscated_files):
        """
        Merge all file splits into one new obfuscated file.
        Get all file parts, sort them by index, merge them one-by-one into a new file.
        Delete
        """
        if not list_obfuscated_files:
            raise utils.NoTextFilesFound("No files to merge!")

        list_obfuscated_files = list(list_obfuscated_files)
        dict_files = defaultdict(list)

        if len(list_obfuscated_files) == 1:
            # move to output_folder
            obfuscated_abs_path = list_obfuscated_files[0]
            orig_basename, _ = os.path.basename(obfuscated_abs_path).split(utils.FILE_PREFIX, maxsplit=1)
            target_dir = os.path.dirname(obfuscated_abs_path.replace(self._files_tmp_folder, ''))
            target_dir = self.args.output_folder + target_dir.strip("/")
            utils.create_folder(target_dir)
            shutil.move(obfuscated_abs_path, os.path.join(target_dir, orig_basename))
        else:
            # Sort parts by initial index to merge them by order
            list_obfuscated_files = sorted(list_obfuscated_files, key=utils.sort_func)

            for obfuscated_abs_path in list_obfuscated_files:
                orig_basename, _ = os.path.basename(obfuscated_abs_path).split(utils.FILE_PREFIX, maxsplit=1)
                target_dir = os.path.dirname(obfuscated_abs_path.replace(self._files_tmp_folder, ''))
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
        utils.logger.debug(f"Merge {output_file}")
        utils.combine_files(list_files=list_files, output_file=output_file)
        utils.remove_files(list_files=list_files)
