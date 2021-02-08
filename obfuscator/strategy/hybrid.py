from strategy.abs_file_splitter import FileSplitters
from strategy.low_level import ObfuscateLowLevel
from strategy.split_in_place import ObfuscateSplitInPlace


class FileToObfuscate:
    def __init__(self, pre, obfuscate, post, src_file):
        self.pre = pre
        self.obfuscate = obfuscate
        self.post = post
        self.obfuscated_file = None
        self.src_file: str = src_file

    def hybrid_obfuscate(self):
        self.obfuscated_file = self.obfuscate(self.src_file)
        return self

    def post_it(self, pool, obfuscated_files):
        return self.post(pool, obfuscated_files)


class ObfuscateHybrid(FileSplitters):
    def __init__(self, args, name=None):
        super().__init__(args, name=name or "Hybrid")
        self.threshold = getattr(args, 'threshold', 100)
        self.low_level = ObfuscateLowLevel(args)
        self.in_place = ObfuscateSplitInPlace(args)

    def pre_all(self):
        super().pre_all()
        self.low_level.pre_all()
        self.in_place.pre_all()

    def pre_one(self, src_file):
        chosen = self.low_level if self.low_level.can_run(src_file, threshold=self.threshold) else self.in_place
        return [FileToObfuscate(chosen.pre_one, chosen.obfuscate_one, chosen.post_one, src_file=src_file)]

    def obfuscate_one(self, src_file: FileToObfuscate):
        return src_file.hybrid_obfuscate()

    def post_one(self, pool, obfuscated_files, *args, **kwargs):
        return obfuscated_files[0].post_it(pool=pool, obfuscated_files=[f.obfuscated_file for f in obfuscated_files])

    def post_all(self):
        super().post_all()
        self.low_level.post_all()
        self.in_place.post_all()
