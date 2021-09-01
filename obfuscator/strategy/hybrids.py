from strategy.abs_file_splitter import AbsHybrid
from strategy.low_level import ObfuscateLowLevel
from strategy.split_and_merge import ObfuscateSplitAndMerge
from strategy.split_in_place import ObfuscateSplitInPlace


class ObfuscateHybrid(AbsHybrid):
    def __init__(self, args, name=None):
        strategies = {True: ObfuscateLowLevel(args), False: ObfuscateSplitInPlace(args)}

        super().__init__(
            args,
            name=name or "HybridLowLevelSplit",
            strategies=strategies,
            main_strategy=strategies[True],
        )

        self.pipeline = [
            (self.main_strategy.orchestrate_iterator, 5),
            (self.orchestrator.decide, 2),
            (self.orchestrator.obfuscate_file, 8),
        ]


class ObfuscateHybridSplit(AbsHybrid):
    def __init__(self, args, name=None):
        strategies = {
            True: ObfuscateSplitAndMerge(args),
            False: ObfuscateSplitInPlace(args),
        }

        super().__init__(
            args,
            name=name or "HybridSplits",
            strategies=strategies,
            main_strategy=strategies[True],
        )

        self.pipeline = [
            (self.main_strategy.orchestrate_iterator, 1),
            (self.orchestrator.decide, 1),
            (self.orchestrator.obfuscate_file, 10),
        ]
