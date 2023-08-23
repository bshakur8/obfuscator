from .abs_file_splitter import AbsHybrid
from .low_level import ObfuscateLowLevel
from .split_and_merge import ObfuscateSplitAndMerge
from .split_in_place import ObfuscateSplitInPlace


class ObfuscateHybrid(AbsHybrid):
    def __init__(self, args, name: str = "HybridLowLevelSplit"):
        strategies = {True: ObfuscateLowLevel(args), False: ObfuscateSplitInPlace(args)}

        super().__init__(args, name=name, strategies=strategies, main_strategy=strategies[True])

        self.pipeline = [
            (self.main_strategy.orchestrate_iterator, 5),
            (self.orchestrator.decide, 2),
            (self.orchestrator.obfuscate_file, 8),
        ]


class ObfuscateHybridSplit(AbsHybrid):
    def __init__(self, args, name: str = "HybridSplits"):
        strategies = {True: ObfuscateSplitAndMerge(args), False: ObfuscateSplitInPlace(args)}

        super().__init__(args, name=name, strategies=strategies, main_strategy=strategies[True])

        self.pipeline = [
            (self.main_strategy.orchestrate_iterator, 1),
            (self.orchestrator.decide, 1),
            (self.orchestrator.obfuscate_file, 10),
        ]
