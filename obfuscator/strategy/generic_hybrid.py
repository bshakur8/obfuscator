from strategy import utils
from strategy.abs_file_splitter import FileSplitters


class ObfuscateGenericHybrid(FileSplitters):

    def __init__(self, args, strategies, name=None):
        super().__init__(args, name=name or "GenericHybrid")
        self.strategies = list(strategies.values())
        self.strategy_to_worker = {}

        for idx, (flag, strategy) in enumerate(strategies.items(), 1):
            # worker = ObfuscateWorker(name=strategy.__str__(), function_to_run=strategy.single_obfuscate, idx=idx)
            # worker.start()
            self.strategy_to_worker[flag] = strategy.single_obfuscate

    def pre_all(self):
        super().pre_all()
        with self.management_pool(len(self.strategies)) as pool:
            pool.map(utils.dummy, (o.pre_all for o in self.strategies))

    def single_obfuscate(self, abs_file, *args, **kwargs):
        raise NotImplemented()

    def obfuscate(self):
        main_strategy = self.strategies[0]
        main_strategy.orchestrate_workers(raw_files=self.raw_files,
                                          strategy_to_worker=self.strategy_to_worker)

    def obfuscate_one(self, *args, **kwargs):
        raise NotImplemented()

    def post_all(self):
        super().post_all()
        with self.management_pool(self.args.workers) as pool:
            pool.map(utils.dummy, (o.post_all for o in self.strategies))
