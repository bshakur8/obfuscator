from queue import Queue

from strategy import utils
from strategy.abs_file_splitter import FileSplitters
from strategy.workers import ObfuscateWorker


class ObfuscateGenericHybrid(FileSplitters):

    def __init__(self, args, strategies, name=None):
        super().__init__(args, name=name or "GenericHybrid")
        self.strategies = list(strategies.values())
        self.strategy_to_worker = {}

        for flag, strategy in strategies.items():
            worker = ObfuscateWorker(strategy=strategy, queue_class=Queue)
            worker.start()
            self.strategy_to_worker[flag] = worker

    def pre_all(self):
        super().pre_all()
        with self.management_pool(len(self.strategies)) as pool:
            pool.map(utils.dummy, (o.pre_all for o in self.strategies))

    def single_obfuscate(self, abs_file):
        raise NotImplemented()

    def obfuscate(self):
        main_strategy = self.strategies[0]
        main_strategy.orchestrate_workers(raw_files=self.raw_files,
                                          strategy_to_worker=self.strategy_to_worker)

    def obfuscate_one(self, src_file):
        raise NotImplemented()

    def post_all(self):
        super().post_all()
        with self.management_pool(self.args.workers) as pool:
            pool.map(utils.dummy, (o.post_all for o in self.strategies))
