#!/usr/bin/env python3
import os
from abc import ABCMeta
from enum import Enum

from strategy.workers_pool import WorkersPool
from strategy import utils
from detectors.detectors import ObfuscatorDetectors
from detectors.scrubber import ObfuscatorScrubber


class RCEnum(Enum):
    SUCCESS = 0
    IGNORED = 1
    FAILURE = 2


class FileSplitters(metaclass=ABCMeta):

    def __init__(self, args, name):
        self.args = args
        self.name = name
        self.raw_files = []  # # List of files to obfuscate
        self._scrubber = None
        self.pool_function = WorkersPool.pool_factory(debug=args.debug, pool_type=args.pool_type)

        # Set args workers to be the pool's default workers number
        self.args.workers = self.args.workers or self.pool_function().workers
        utils.logger.info(f"Working with Pool: {self.pool_function}, with {self.args.workers} workers")

        if not self.args.output_folder:
            # make output folder - input folder
            self.args.output_folder = self.args.input_folder if os.path.isdir(self.args.input_folder)\
                else os.path.dirname(self.args.input_folder)

    def __str__(self):
        return f"Strategy: {self.name}: PoolType: {self.pool_function}"

    def _print(self, src_file):
        msg = f"Obfuscate {self.name}: " + "{size}{src_file}"
        size_unit = ''
        if self.args.debug:
            _, size_unit = utils.get_size(self.args.input_folder, src_file)
            size_unit = f'{size_unit} '
        utils.logger.info(msg.format(size=size_unit, src_file=src_file))

    def run(self):
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

    @property
    def scrubber(self):
        return self._scrubber

    @scrubber.setter
    def scrubber(self, scrubber):
        # setting scrubber from outside: loosely coupled
        self._scrubber = scrubber

    def customise_scrubber(self):
        scrubber = ObfuscatorScrubber()

        for detector in ObfuscatorDetectors:
            detector.filth_cls.salt = self.args.salt
            utils.logger.debug(f"Add Detector: {detector}")
            scrubber.add_detector(detector)

        self.scrubber = scrubber

    def pre_all(self):
        """ Pre operations"""
        pass

    def post_all(self):
        """Post operations"""
        pass

    def obfuscate(self):
        """Obfuscate input files:
         - If there's only one workers or one file: Run in single process without multiprocessing Pool
        """
        if not self.raw_files:
            raise utils.NoTextFilesFound(f"No files to obfuscate")

        with self.pool_function(self.args.workers) as pool:
            for src_file in self.raw_files:
                files_to_obfuscate = self.pre_one(src_file)
                obfuscated_files = self.obfuscate_all(pool, files_to_obfuscate)
                self.post_one(pool, obfuscated_files)
                utils.logger.debug(f"Done obfuscate '{src_file}'")

    def obfuscate_all(self, pool, files_to_obfuscate):
        # If 1 worker or one file to handle: run single process
        return pool.map(self.obfuscate_one, files_to_obfuscate)

    def pre_one(self, src_file):
        return [src_file]

    def obfuscate_one(self, src_file):
        raise NotImplementedError()

    def post_one(self, *args, **kwargs):
        pass
