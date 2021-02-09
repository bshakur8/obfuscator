#!/usr/bin/env python3
import os
from abc import ABCMeta
from enum import Enum

from strategy import utils
from strategy.workers_pool import WorkersPool


class RCEnum(Enum):
    SUCCESS = 0
    IGNORED = 1
    FAILURE = 2


class FileSplitters(metaclass=ABCMeta):

    def __init__(self, args, name):
        self.args = args
        self.name = name
        self.raw_files = []  # # List of files to obfuscate
        self._pool_function = None

        self.pool_function = WorkersPool.pool_factory(self.args.debug, pool_type=self.args.pool_type)
        # Set args workers to be the pool's default workers number
        self.args.workers = self.args.workers or self.pool_function().workers

        if not self.args.output_folder:
            # make output folder - input folder
            self.args.output_folder = self.args.input_folder if os.path.isdir(self.args.input_folder) \
                else os.path.dirname(self.args.input_folder)

    @property
    def management_pool(self):
        return WorkersPool.pool_factory(debug=self.args.debug, pool_type=None, mgmt=True)

    def __str__(self):
        return self.name

    def _print(self, src_file):
        msg = f"Obfuscate {self.name}: " + "{size}{src_file}"
        size_unit = ''
        if self.args.debug:
            _, size_unit = utils.get_file_size(src_file)
            size_unit = f'{size_unit} '
        utils.logger.info(msg.format(size=size_unit, src_file=src_file))

    def run(self):
        utils.logger.info(f"Working with pool {self.pool_function.__name__} with {self.args.workers} workers")
        # Template
        try:
            utils.create_folder(self.args.output_folder)
            self.raw_files = utils.get_txt_files(self.args)
            self.pre_all()
            self.obfuscate()
            utils.logger.info(f"SUCCESS: Results can be found in '{self.args.output_folder}'")
            rc = RCEnum.SUCCESS

        except utils.NoTextFilesFound as e:
            utils.logger.warning(str(e))
            rc = RCEnum.IGNORED

        except Exception:
            utils.logger.exception(f"FAILED")
            rc = RCEnum.FAILURE
        finally:
            self.post_all()
        return rc.value

    def pre_all(self):
        """ Pre operations"""
        pass

    def post_all(self):
        """Post operations"""
        pass

    def orchestrate_workers(self, raw_files, *args, **kwargs):
        raise NotImplemented("Not Supported")

    def single_obfuscate(self, abs_file, *args, **kwargs):
        files_to_obfuscate = self.pre_one(abs_file)
        with self.pool_function(len(files_to_obfuscate)) as pool:
            obfuscated_files = self.obfuscate_all(pool, files_to_obfuscate, *args, **kwargs)
            self.post_one(pool, obfuscated_files)
        utils.logger.debug(f"Done obfuscate '{abs_file}'")

    def obfuscate(self):
        """Obfuscate input files:
         - If there's only one workers or one file: Run in single process without multiprocessing Pool
        """
        if not self.raw_files:
            raise utils.NoTextFilesFound(f"{self.__str__()} No files to obfuscate")

        with self.pool_function(self.args.workers) as pool:
            for src_file in self.raw_files:
                files_to_obfuscate = self.pre_one(src_file)
                obfuscated_files = self.obfuscate_all(pool, files_to_obfuscate)
                self.post_one(pool, obfuscated_files)
                utils.logger.debug(f"Done obfuscate '{src_file}'")

    def obfuscate_all(self, pool, files_to_obfuscate, *args):
        # If 1 worker or one file to handle: run single process
        listargs = [(f, utils.itemgetter(args, 0, dict)) for f in files_to_obfuscate]
        return pool.map(self.obfuscate_one, listargs)

    def pre_one(self, src_file):
        return [src_file]

    def obfuscate_one(self, *args, **kwargs):
        raise NotImplementedError()

    def post_one(self, *args, **kwargs):
        pass
