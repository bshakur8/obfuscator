#!/usr/bin/env python3
import os
import random
from abc import ABCMeta
from functools import lru_cache, partial

from strategy import utils
from strategy.enums import RCEnum
from strategy.workers_pool import WorkersPool, MultiProcessPipeline


class BaseFileSplitters(metaclass=ABCMeta):
    def __init__(self, args, name):
        self.args = args
        self.name = name
        self.raw_files = []  # List of files to obfuscate
        self._pool_function = None

        self.pool_function = WorkersPool.pool_factory(
            self.args.debug, pool_type=self.args.pool_type
        )
        # Set args workers to be the pool's default workers number
        self.args.workers = self.args.workers or self.pool_function().workers

        if not self.args.output_folder:
            # make output folder - input folder
            self.args.output_folder = (
                self.args.input_folder
                if os.path.isdir(self.args.input_folder)
                else os.path.dirname(self.args.input_folder)
            )

    @property
    def management_pool(self):
        return WorkersPool.pool_factory(
            debug=self.args.debug, pool_type=None, mgmt=True
        )

    def __str__(self):
        return self.name

    def _print(self, src_file):
        msg = f"Obfuscate {self.name}: " + "{size}{src_file}"
        size_unit = ""
        if self.args.debug:
            _, size_unit = utils.get_file_size(src_file)
            size_unit = f"{size_unit} "
        utils.logger.info(msg.format(size=size_unit, src_file=src_file))

    def run(self):
        utils.logger.info(
            f"Working with pool {self.pool_function.__name__} with {self.args.workers} workers"
        )
        # Template
        try:
            utils.create_folder(self.args.output_folder)
            self.raw_files = utils.get_txt_files(self.args)
            self.pre_all()
            self.obfuscate()
            utils.logger.info(
                f"SUCCESS: Results can be found in '{self.args.output_folder}'"
            )
            rc = RCEnum.SUCCESS

        except utils.NoTextFilesFound as e:
            utils.logger.warning(str(e))
            rc = RCEnum.IGNORED

        except (BaseException,):
            # BaseException: to catch also KeyboardInterrupt
            utils.logger.exception(f"FAILED")
            rc = RCEnum.FAILURE
        finally:
            self.post_all()
        return rc.value

    def pre_all(self):
        """Pre operations"""

    def post_all(self):
        """Post operations"""

    def orchestrate_run(self):
        raise NotImplemented("Not Supported")

    def orchestrate_iterator(self, src_file, *args, **kwargs):
        return src_file, random.choice((True, False)), None

    def single_obfuscate(self, abs_file, *args, **kwargs):
        files_to_obfuscate = self.pre_one(abs_file)
        with self.pool_function(len(files_to_obfuscate)) as pool:
            obfuscated_files = self.obfuscate_all(pool, files_to_obfuscate, *args)
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
        args = [(f, utils.itemgetter(args, 0, dict)) for f in files_to_obfuscate]
        return pool.map(self.obfuscate_one, args)

    def pre_one(self, src_file):
        return [src_file]

    def obfuscate_one(self, *args, **kwargs):
        raise NotImplementedError()

    def post_one(self, *args, **kwargs):
        pass


class ObfuscateGenericHybrid(BaseFileSplitters):
    def __init__(self, args, hybrid, name=None):
        super().__init__(args, name=name or "GenericHybrid")
        self.hybrid = hybrid

    def pre_all(self):
        super().pre_all()
        with self.management_pool(len(self.hybrid.strategies)) as pool:
            pool.map(utils.dummy, (o.pre_all for o in self.hybrid.strategies.values()))

    def single_obfuscate(self, abs_file, *args, **kwargs):
        assert False

    def obfuscate(self):
        return self.hybrid.orchestrate_run()

    def obfuscate_one(self, *args, **kwargs):
        assert False

    def post_all(self):
        super().post_all()
        with self.management_pool(self.args.workers) as pool:
            pool.map(utils.dummy, (o.post_all for o in self.hybrid.strategies.values()))


class AbsHybrid(BaseFileSplitters):
    def __init__(self, args, name, strategies, main_strategy):
        super().__init__(args, name)
        self.default_process_num = 5
        self.pipeline = None
        self.strategies = strategies
        self.main_strategy = main_strategy
        self.strategy_to_worker = {
            flag: strategy.single_obfuscate for flag, strategy in strategies.items()
        }

    @property
    @lru_cache(1)
    def generic(self):
        return ObfuscateGenericHybrid(self.args, hybrid=self)

    def obfuscate_one(self, *args, **kwargs):
        assert False

    def single_obfuscate(self, abs_file, *args, **kwargs):
        assert False

    def pre_all(self):
        self.generic.raw_files = self.raw_files
        return self.generic.pre_all()

    def pre_one(self, src_file):
        return self.generic.pre_one(src_file)

    def obfuscate(self):
        return self.generic.obfuscate()

    def post_one(self, *args, **kwargs):
        return self.generic.post_one(*args, **kwargs)

    def post_all(self):
        return self.generic.post_all()

    def orchestrate_run(self):
        MultiProcessPipeline(self.pipeline, self.raw_files, self.default_process_num)(
            ignore_results=True
        )

    @property
    @lru_cache(1)
    def orchestrator(self):
        return self.Orchestrator(self)

    class Orchestrator:
        """
        Helper class for hybrid classes.
        """

        def __init__(self, hybrid):
            self.hybrid = hybrid

        def decide(self, data):
            src_file, move_to_main_strategy, future_args = data
            if future_args is None:
                future_args = tuple()
            if move_to_main_strategy is None:
                utils.logger.info(
                    f"{self.hybrid.main_strategy}: ignore file {src_file}"
                )
                return None
            return partial(self.hybrid.strategy_to_worker[move_to_main_strategy])(
                src_file, future_args
            )

        @staticmethod
        def obfuscate_file(obf_func):
            if obf_func:
                return obf_func()
            return None
