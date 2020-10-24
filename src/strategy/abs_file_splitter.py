#!/usr/bin/env python3
import os
from abc import ABCMeta
from enum import Enum

from .workers_pool import WorkersPool
from .. import utils
from ..detectors.detectors import ObfuscatorDetectors
from ..detectors.scrubber import ObfuscatorScrubber
from ..utils import NoTextFilesFound


class RCEnum(Enum):
    SUCCESS = 0
    IGNORED = 1
    FAILURE = 2


class FileSplitters(metaclass=ABCMeta):
    # Save in memory before going to disk
    BUFFER_SIZE = 5000

    def __init__(self, args, name):
        self.args = args
        self.name = name
        self._scrubber = None

        self.pool_function = WorkersPool.pool_factory(pool_type=args.pool_type)

        # Set args workers to be the pool's default workers number
        self.args.workers = self.args.workers or self.pool_function().workers
        utils.logger.info(f"Working with Pool: {self.pool_function}, with {self.args.workers} workers")

        # List of files to obfuscate
        self.list_raw_files = []

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
            self._pre()
            self._obfuscate()
            utils.logger.info(f"SUCCESS")
            utils.logger.info(f"Results can be found in '{self.args.output_folder}'")
            rc = RCEnum.SUCCESS

        except NoTextFilesFound as e:
            utils.logger.warning(str(e))
            rc = RCEnum.IGNORED

        except Exception:
            utils.logger.error(f"FAILED")
            rc = RCEnum.FAILURE
            import traceback
            utils.logger.error(traceback.format_exc())
        finally:
            self._post()

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

        for det in ObfuscatorDetectors:
            utils.logger.debug(f"Add Detector: {det}")
            det.filth_cls.salt = self.args.salt
            scrubber.add_detector(det)

        self.scrubber = scrubber

    def _get_txt_files(self):
        """ Get text files to handle
        :return: List of text files
        :rtype: List[str]
        """
        if os.path.isdir(self.args.input_folder):
            list_txt_files = utils.get_txt_files(self.args.input_folder, ignore_hint=self.args.ignore_hint)
        else:
            # file
            list_txt_files = [self.args.input_folder]

        return list_txt_files

    def _pre(self):
        """ Pre operations"""
        utils.create_folder(self.args.output_folder)

    def _post(self):
        """Post operations"""
        pass

    def _obfuscate(self):
        raise NotImplementedError()
