from strategy.abs_file_splitter import FileSplitters
from strategy.generic_hybrid import ObfuscateGenericHybrid
from strategy.low_level import ObfuscateLowLevel
from strategy.split_in_place import ObfuscateSplitInPlace


class ObfuscateHybrid(FileSplitters):

    def __init__(self, args, name=None):
        super().__init__(args, name=name or "Hybrid")
        strategies = {True: ObfuscateLowLevel(args, threshold=args.threshold),
                      False: ObfuscateSplitInPlace(args)}
        self._generic = ObfuscateGenericHybrid(args, strategies=strategies)

    def obfuscate_one(self, *args, **kwargs):
        raise NotImplemented()

    def single_obfuscate(self, abs_file, *args, **kwargs):
        raise NotImplemented()

    def pre_all(self):
        self._generic.raw_files = self.raw_files
        return self._generic.pre_all()

    def pre_one(self, src_file):
        return self._generic.pre_one(src_file)

    def obfuscate(self):
        return self._generic.obfuscate()

    def post_one(self, *args, **kwargs):
        return self._generic.post_one(*args, **kwargs)

    def post_all(self):
        return self._generic.post_all()
