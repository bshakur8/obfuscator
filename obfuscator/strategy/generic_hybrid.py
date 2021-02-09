from functools import partial
from math import ceil

from strategy import utils
from strategy.abs_file_splitter import FileSplitters


class ObfuscateGenericHybrid(FileSplitters):

    def __init__(self, args, strategies, name=None):
        super().__init__(args, name=name or "GenericHybrid")
        self.strategies = strategies

    def pre_all(self):
        super().pre_all()
        with self.management_pool(self.args.workers) as pool:
            pool.map(utils.dummy, (o.pre_all for o in self.strategies))

        with self.management_pool(self.args.workers) as pool:
            pool.map(utils.dummy, (partial(s.filter_raw_files, raw_files=self.raw_files) for s in self.strategies[:-1]))

        for strategy in self.strategies[:-1]:
            for raw_file in set(self.raw_files) - set(strategy.raw_files):
                self.strategies[-1].raw_files.append(raw_file)

        for idx, strategy in enumerate(self.strategies[:-1]):
            if not strategy.raw_files:
                # one percent of the files or 1
                self.strategies[idx].raw_files = self.get_part(self.strategies[-1].raw_files, percent=0.01)

    @staticmethod
    def get_part(collection, percent=0.1):
        return list(collection)[0: max(1, ceil(percent * len(collection)))]

    def obfuscate(self):
        with self.management_pool(self.args.workers) as pool:
            pool.map(utils.dummy, (o.obfuscate for o in self.strategies))

    def obfuscate_one(self, src_file):
        raise NotImplemented()

    def post_all(self):
        super().post_all()
        with self.management_pool(self.args.workers) as pool:
            pool.map(utils.dummy, (o.post_all for o in self.strategies))
