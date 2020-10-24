#!/usr/bin/env python3
import argparse
import shutil
from itertools import chain
import math
import os
import re
import subprocess
import time
from collections import namedtuple
from functools import wraps
from typing import List

import logging

LIST_UNITS = ["bytes", "KB", "MB", "GB", "GB+"]
FILE_PREFIX = "___"
TMP_FOLDER_PREFIX = "obf_tmp_"
PART_SUFFIX = "{0}pt{0}".format(FILE_PREFIX)
NEW_FILE_SUFFIX = "{0}new".format(FILE_PREFIX)
BUILTIN_IGNORE_HINT = "-DONT-OBFUSCATE-ME-"
BUILTIN_IGNORE_HINT_RE = re.compile(BUILTIN_IGNORE_HINT)

# logger object
logger = logging.getLogger("Obfuscator")


def init_logger(args=None):
    """
    Init logger:
     - Set streamHandler
     - Set FileHandler

    :param args: argsparse args. Uses 'log_folder' and 'verbose'
    """
    handler = logging.StreamHandler()
    log_format = u'%(asctime)s [%(levelname)-1s %(process)d]  %(message)s'
    handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(handler)
    level = logging.DEBUG
    msg = None

    if args:
        if args.log_folder:
            logging.basicConfig(filename=os.path.join(args.log_folder, "obfuscation_log"), level=logging.DEBUG,
                                format=log_format)
        if args.verbose:
            level = logging.DEBUG
            msg = f"verbose mode is active"
        else:
            level = logging.INFO
            msg = f"verbose mode is inactive"

    logger.setLevel(level)
    logger.debug(BUILTIN_IGNORE_HINT)
    if msg:
        logger.debug(msg)


def get_txt_files(logs_dir, ignore_hint=None):
    """
    Get text files to obfuscate

    :param logs_dir: str, Folder to iterate
    :param ignore_hint: str, String for regex for ignoring files
    :return: List[str], List of text files inside folder
    """
    all_files = []

    def onerror(exc_inst):
        logger.warning(f"Failed to read file: {exc_inst.filename}\n{str(exc_inst)}")

    ignore_hint_re = re.compile(ignore_hint) if ignore_hint else None

    for root, dirs, files in os.walk(logs_dir, onerror=onerror):
        for folder in dirs:
            if folder.endswith(TMP_FOLDER_PREFIX):
                logger.warning(f"ignore folder: {os.path.join(root, folder)}")
                continue

        for file in files:
            abs_file = os.path.join(root, file)

            if NEW_FILE_SUFFIX in file or PART_SUFFIX in file or file.endswith(".dat"):
                logger.warning(f"ignore file: {abs_file}")
                continue

            # buffering = 1 works for text files only
            # "r" read text with utf-8 encoding
            try:
                with open(abs_file, "r", buffering=1, encoding="utf-8", errors="backslashreplace") as fd:
                    try:
                        line = fd.readline()
                        if line:
                            # read one line, check if line is not empty
                            # stop reading after finding first valid line
                            if BUILTIN_IGNORE_HINT_RE.search(line) \
                                    or (ignore_hint_re is not None and ignore_hint_re.search(line)):
                                logger.warning(f"ignore file: {abs_file}")
                            else:
                                logger.warning(f"Text file: {abs_file}")
                                all_files.append(abs_file)
                    except UnicodeDecodeError:
                        logger.warning(f"Probably a binary file: {abs_file}")
                        continue
            except PermissionError as e:
                logger.warning(f"{str(e)}")

    return all_files


def remove_files(list_files):
    """Remove list of files"""
    for f in list_files:
        try:
            os.remove(f)
        except OSError:
            pass


def create_folder(folder):
    """
    :param folder: Folder to create
    """
    if not os.path.isfile(folder):
        os.makedirs(folder, exist_ok=True)


def get_size(path):
    """
    :param path: str, File path
    :return: tuple, Original size, size + unit to to display
    """
    orig_size = os.stat(path).st_size
    size = int(orig_size)

    unit = "Nan"
    for unit in LIST_UNITS:
        if size < 1024.0:
            break
        size /= 1024.0

    return orig_size, f"{size:.2f} {unit}"


# RC return object
RC = namedtuple("RC", "rc stdout stderr")


def run_local_cmd(cmd, cmd_input=None, log_to_debug=True):
    """
    Run local OS command

    :param cmd: str, Command to run
    :param log_to_debug: bool, True iff log command and results to debug log
    :param cmd_input: stdin stream
    :return: str, stdout
    """
    if log_to_debug:
        logger.debug(f"IN: {cmd}")

    kwargs = dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                  bufsize=1, universal_newlines=True, shell=True, check=True, input=cmd_input)

    rc = subprocess.run(cmd, **kwargs)

    if log_to_debug:
        logger.debug(f"OUT: [RC={rc.returncode}: {cmd}\nstdout={rc.stdout}\nstderr={rc.stderr}")

    rc = RC(rc, try_decode(rc.stdout), try_decode(rc.stderr))
    return rc


def try_decode(obj: bytes, encoding='utf-8'):
    """
    Try decode given bytes with encoding (default utf-8)
    :return: Decoded bytes to string if succeeded, else object itself
    """
    try:
        rc = obj.decode(encoding=encoding)
    except AttributeError:
        rc = obj
    return rc.strip()


def get_lines_number(path: str) -> int:
    """
    :param path: str, absolute filename path to get lines number
    :return: File number of lines
    """
    rc = run_local_cmd(cmd=f"wc -l {path}")
    line = rc.stdout.strip()
    return int(line.split(" ")[0].strip())


def get_extended_file(filename, size_limit, num_parts, output_folder):
    """
    Iterate list files and split the files which size is above
     size_limit into num_parts parts and put parts in output_folder

    :param filename: str, File to check
    :param size_limit: int, size limit to decide on split
    :param num_parts: int, Number of parts to split file into
    :param output_folder: str, output folder to save parts in
    :return: List[str], list of absolute files paths
    """
    size, size_unit = get_size(filename)
    logger.debug(f"File [{size_unit}]: {filename}")
    if num_parts == 1 or size < size_limit:
        # Single worker: no need to split
        return [filename]
    else:
        # File size is bigger than limit and workers > 1
        return split_file(filename, num_parts, output_folder)


def get_extended_file_list(files, size_limit, num_parts, output_folder):
    """
    Iterate list files and split the files which size is above
     size_limit into num_parts parts and put parts in output_folder

    :param files: List[str], List of files to iterate
    :param size_limit: int, size limit to decide on split
    :param num_parts: int, Number of parts to split file into
    :param output_folder: str, output folder to save parts in
    :return: List[str], list of absolute files paths
    """
    # Flatten list of lists: ([1,2], [3,4], [5,6], []) ==> [1, 2, 3, 4, 5, 6]
    return list(chain.from_iterable(get_extended_file(f, size_limit, num_parts, output_folder) for f in files))


def get_folders_difference(filename, folder):
    """
    example:
    filename: /a/b/c/file.txt
    folder: /a/b/d
    output: /a/b/d/c/file.txt

    :return: Folders difference between a file and a folder
    """
    basename = os.path.basename(filename)
    common_prefix = os.path.commonpath([folder, filename])
    logger.debug(f"Common prefix: ({filename}) and ({folder}) ==> {common_prefix}")
    # folders to add: clean common (prefix) and basename (suffix)
    if common_prefix == "/":
        # no common_prefix
        folder_suffix = os.path.dirname(filename)
    else:
        folder_suffix = filename.replace(common_prefix, "").replace(basename, "")

    folder += "/" if not folder.endswith("/") else ''
    new_folder_name = f"{folder}{folder_suffix}".replace("//", '/').rstrip("/")

    # create it
    create_folder(new_folder_name)
    return new_folder_name


def clone_file(filename, target_dir, suffix=None):
    """
    Create same file in different directory [Including sub dirs]

    :param filename: str, Filename to clone
    :param target_dir: Target dir
    :param suffix: Suffix to use for renaming
    :return: str, New file absolute path
    """
    # Get basename
    basename = os.path.basename(filename)
    # create new basename
    new_filename = basename + suffix

    # Get common_prefix between filename and targetDir: to calculate the missing dirs to add to target dir
    new_folder_name = get_folders_difference(filename=filename, folder=target_dir)

    # create it
    logger.debug(f"Cloned folder: {new_folder_name}")
    # Get new filepath in target_dir
    new_file_abs = os.path.join(new_folder_name, new_filename)
    logger.debug(f"Cloned file: {new_file_abs}")
    return new_file_abs


def split_file(path: str, num_parts: int, output_folder) -> List[str]:
    """
    Split files:
     - Used Linux split function

    :param path: str, Filepath to split
    :param num_parts: int, Number of parts to split file into
    :param output_folder: str, Output folder to put splits in
    :return: List[str], List of split files
    """
    logger.debug(f"Split file into '{num_parts}' parts: {path}")

    # ceil is better for fairness
    num_lines_per_file = math.ceil(get_lines_number(path) / num_parts)
    lines_per_file = max(1, num_lines_per_file)
    # in case number of lines < num parts
    logger.debug(f"Split file={path}: parts={num_parts}, lines={num_lines_per_file}, lines_per_file= {lines_per_file}")
    part_abs_path = clone_file(filename=path, target_dir=output_folder, suffix=PART_SUFFIX)

    cmd = f"split -d -l {num_lines_per_file} {path} {part_abs_path}"
    _ = run_local_cmd(cmd=cmd)

    part_name = f"{os.path.basename(path)}{PART_SUFFIX}"
    files = [os.path.join(root, f) for root, dirs, files in os.walk(output_folder) for f in files
             if f and f.startswith(part_name)]

    logger.debug(f"File={path}, files={files}")
    return files


def combine_files(list_files: List[str], output_file: str, buffering=5000) -> None:
    """
    :param list_files: List[str], [Sorted] list files to read sequentially
    :param output_file: str, output filename to merge files into
    :param buffering: int, buffering files to read, write
    """
    with open(output_file, 'w', buffering=buffering) as dst:
        for f in list_files:
            with open(f, "r", buffering=buffering) as src:
                shutil.copyfileobj(src, dst)


def measure_time(func):
    """
    Time measurement decorator

    :param func: Function to measure
    :return: Callable, wrapped func
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        t1 = time.time()
        result = func(*args, **kwargs)
        logger.debug(f"'{func.__name__}' function took: {time.time() - t1} seconds")
        return result
    return wrapper


def sort_func(x):
    """ Sort function by index
    :param x: Item to sort
    """
    try:
        return int(x.split(FILE_PREFIX)[-3])
    except (IndexError, ValueError):
        return 0


# Custom argparse type representing a bounded int
class IntRange:

    def __init__(self, imin=None, imax=None):
        self.imin = imin
        self.imax = imax

    def __call__(self, arg):
        try:
            value = int(arg)
        except ValueError:
            raise self.exception()
        if (self.imin is not None and value < self.imin) or (self.imax is not None and value > self.imax):
            raise self.exception()
        return value

    def exception(self):
        if self.imin is not None and self.imax is not None:
            return argparse.ArgumentTypeError(f"Must be an integer in the range [{self.imin}, {self.imax}]")
        elif self.imin is not None:
            return argparse.ArgumentTypeError(f"Must be an integer >= {self.imin}")
        elif self.imax is not None:
            return argparse.ArgumentTypeError(f"Must be an integer <= {self.imax}")
        else:
            return argparse.ArgumentTypeError("Must be an integer")


class PathType:
    """
    Path type that gets a path and checks if it really exist
    """

    def __init__(self, verify_exist=False):
        self.verify_exist = verify_exist

    def __call__(self, path):
        """
        :return: str, Path if valid
        :raises: argparse.ArgumentTypeError, Path is none or not exist
        """
        if path:
            if self.verify_exist:
                os.makedirs(path, exist_ok=True)

            if os.path.isdir(path) or os.path.isfile(path):
                return path

        raise argparse.ArgumentTypeError(f"path is not found: {path}")


class NoTextFilesFound(Exception):
    pass
