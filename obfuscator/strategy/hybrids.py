from obfuscator.strategy.base_spliter import AbsHybrid
from obfuscator.strategy.low_level import ObfuscateLowLevel
from obfuscator.strategy.split_and_merge import ObfuscateSplitAndMerge
from obfuscator.strategy.split_in_place import ObfuscateSplitInPlace


class ObfuscateHybrid(AbsHybrid):
    NAME = "HybridLowLevelSplit"

    def __init__(self, args):
        strategies = {True: ObfuscateLowLevel(args), False: ObfuscateSplitInPlace(args)}
        super().__init__(args, strategies=strategies, main_strategy=strategies[True])

        self.pipeline = [
            (self.main_strategy.orchestrate_iterator, 5),
            (self.orchestrator.decide, 2),
            (self.orchestrator.obfuscate_file, 8),
        ]


class ObfuscateHybridSplit(AbsHybrid):
    NAME = "HybridSplits"

    def __init__(self, args):
        strategies = {
            True: ObfuscateSplitAndMerge(args),
            False: ObfuscateSplitInPlace(args),
        }

        super().__init__(
            args,
            strategies=strategies,
            main_strategy=strategies[True],
        )

        self.pipeline = [
            (self.main_strategy.orchestrate_iterator, 1),
            (self.orchestrator.decide, 1),
            (self.orchestrator.obfuscate_file, 10),
        ]
