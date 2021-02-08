from strategy.abs_file_splitter import FileSplitters
from strategy.low_level import ObfuscateLowLevel
from strategy.split_in_place import ObfuscateSplitInPlace


class ObfuscateHybrid(FileSplitters):
    def __init__(self, args, name=None):
        super().__init__(args, name=name or "Hybrid")
        self.threshold = getattr(args, 'threshold', 100)
        self.low_level = ObfuscateLowLevel(args)
        self.split_merge = ObfuscateSplitInPlace(args)

    def pre_all(self):
        super().pre_all()
        self.low_level.pre_all()
        self.split_merge.pre_all()

    def obfuscate_one(self, src_file):
        if self.low_level.can_run(src_file, threshold=self.threshold):
            return self.low_level.obfuscate_one(src_file)
        else:
            return self.split_merge.obfuscate_one(src_file)
