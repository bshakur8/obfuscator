from functools import partial

from strategy.abs_file_splitter import AbsHybrid
from strategy.low_level import ObfuscateLowLevel
from strategy.split_and_merge import ObfuscateSplitAndMerge
from strategy.split_in_place import ObfuscateSplitInPlace


class ObfuscateHybrid(AbsHybrid):

    def __init__(self, args, name=None):
        strategies = {True: ObfuscateLowLevel(args),
                      False: ObfuscateSplitInPlace(args)}

        super().__init__(args, name=name or "HybridLowLevelSplit", strategies=strategies)

        self.pipeline = [(strategies[True].orchestrate_iterator, 5),
                         (partial(super().orchestrate_decide, self.main_strategy, self.generic.strategy_to_worker), 2),
                         (super().orchestrate_work, 8)]


class ObfuscateHybridSplit(AbsHybrid):

    def __init__(self, args, name=None):
        strategies = {True: ObfuscateSplitAndMerge(args),
                      False: ObfuscateSplitInPlace(args)}

        super().__init__(args, name=name or "HybridSplits", strategies=strategies)

        self.pipeline = [(strategies[True].orchestrate_iterator, 1),
                         (partial(super().orchestrate_decide, self.main_strategy, self.generic.strategy_to_worker), 1),
                         (super().orchestrate_work, 10)]

