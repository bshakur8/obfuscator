from math import ceil

from strategy import utils
from strategy.abs_file_splitter import FileSplitters
from strategy.low_level import ObfuscateLowLevel
from strategy.split_in_place import ObfuscateSplitInPlace


class ObfuscateHybrid(FileSplitters):

    def __init__(self, args, name=None):
        super().__init__(args, name=name or "Hybrid")
        self.low_level = ObfuscateLowLevel(args)
        self.in_place = ObfuscateSplitInPlace(args)
        self.low_level.threshold = getattr(args, 'threshold', 100)

    def pre_all(self):
        super().pre_all()
        with self.management_pool(self.args.workers) as pool:
            pool.map(utils.dummy, [self.low_level.pre_all, self.in_place.pre_all])

        self.low_level.filter_raw_files(raw_files=self.raw_files)

        for raw_file in set(self.raw_files) - set(self.low_level.raw_files):
            self.in_place.raw_files.append(raw_file)

        if not self.low_level.raw_files:
            self.low_level.raw_files = self.get_part(self.in_place.raw_files)

    @staticmethod
    def get_part(collection, percent=0.1):
        return list(collection)[0: max(1, ceil(percent * len(collection)))]

    def obfuscate(self):
        with self.management_pool(self.args.workers) as pool:
            pool.map(utils.dummy, [self.low_level.obfuscate, self.in_place.obfuscate])

    def obfuscate_one(self, src_file):
        raise NotImplemented()

    def post_all(self):
        super().post_all()
        with self.management_pool(self.args.workers) as pool:
            pool.map(utils.dummy, [self.low_level.post_all, self.in_place.post_all])
