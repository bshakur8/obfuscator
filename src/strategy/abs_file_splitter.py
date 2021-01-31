#!/usr/bin/env python3
import os
from abc import ABCMeta
from enum import Enum

import utils
from detectors.detectors import ObfuscatorDetectors, ObfuscatorLookup
from detectors.scrubber import ObfuscatorScrubber
from strategy.workers_pool import WorkersPool


class RCEnum(Enum):
    SUCCESS = 0
    IGNORED = 1
    FAILURE = 2


class FileSplitters(metaclass=ABCMeta):

    def __init__(self, args, name):
        self.args = args
        self.name = name
        self._scrubber = None

        self.pool_function = WorkersPool.pool_factory(pool_type=args.pool_type)

        # Set args workers to be the pool's default workers number
        self.args.workers = self.args.workers or self.pool_function().workers
        utils.logger.info(f"Working with Pool: {self.pool_function}, with {self.args.workers} workers")

        # List of files to obfuscate
        self.raw_files = []

        if not self.args.output_folder:
            # make output folder - input folder
            if os.path.isdir(self.args.input_folder):
                self.args.output_folder = self.args.input_folder
            else:
                self.args.output_folder = os.path.dirname(self.args.input_folder)

        if not self.args.output_folder.endswith("/"):
            self.args.output_folder += "/"

    def __str__(self):
        return f"Strategy: {self.name}: PoolType: {self.pool_function}"

    def run(self):
        # Template
        try:
            self.pre()
            self.obfuscate()
            utils.logger.info(f"SUCCESS")
            utils.logger.info(f"Results can be found in '{self.args.output_folder}'")
            rc = RCEnum.SUCCESS

        except utils.NoTextFilesFound as e:
            utils.logger.warning(str(e))
            rc = RCEnum.IGNORED

        except Exception:
            utils.logger.error(f"FAILED")
            rc = RCEnum.FAILURE
            import traceback
            utils.logger.error(traceback.format_exc())
        finally:
            self.post()
        return rc.value

    @property
    def scrubber(self):
        return self._scrubber

    @scrubber.setter
    def scrubber(self, scrubber):
        # setting scrubber from outside: loosely coupled
        self._scrubber = scrubber

    def set_default_scrubber(self):
        scrubber = ObfuscatorScrubber()

        pool_lookup_table = self.pool_function().lookup_table
        for det in ObfuscatorDetectors:
            det.filth_cls.salt = self.args.salt
            lookup_table = det.filth_cls.lookup.table
            det.filth_cls.lookup = ObfuscatorLookup(collection=pool_lookup_table)
            # Show memory address of lookup to verify that table is the same among all threads\processes
            utils.logger.debug(f"Add Detector: {det}: {type(lookup_table)}, {hex(id(lookup_table))}")
            scrubber.add_detector(det)

        self.scrubber = scrubber

    def pre(self):
        """ Pre operations"""
        utils.create_folder(self.args.output_folder)
        self.raw_files = utils.get_txt_files(self.args)
        if not self.raw_files:
            raise utils.NoTextFilesFound(f"No files to obfuscate")

    def post(self):
        """Post operations"""
        pass

    def obfuscate(self):
        raise NotImplementedError()
