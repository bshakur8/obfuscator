#!/usr/bin/env python3
import argparse
import sys

from strategy import utils
from strategy.enums import StrategyTypes
from strategy.hybrids import ObfuscateHybrid, ObfuscateHybridSplit
from strategy.low_level import ObfuscateLowLevel, ObfuscateUsingRipGrep
from strategy.split_and_merge import ObfuscateSplitAndMerge
from strategy.split_in_place import ObfuscateInplace, ObfuscateSplitInPlace
from strategy.workers_pool import WorkersPool

OBFUSCATION_METHODS_FACTORY = {
    StrategyTypes.IN_PLACE: ObfuscateInplace,
    StrategyTypes.SAM: ObfuscateSplitAndMerge,
    StrategyTypes.SAP: ObfuscateSplitInPlace,
    StrategyTypes.LOW_LEVEL: ObfuscateLowLevel,
    StrategyTypes.HYBRID: ObfuscateHybrid,
    StrategyTypes.HYBRID_SPLIT: ObfuscateHybridSplit,
    StrategyTypes.RIPGREP: ObfuscateUsingRipGrep,
}

SIZE_TO_SPLIT_IN_BYTES = 5 * 1024 * 1024  # in bytes - 5 MB


def get_args_parser(test=False):
    thread_pool_choices = WorkersPool.choices()
    default_pool = WorkersPool.get_default_pool_class().__name__

    parser = argparse.ArgumentParser(description="Text files src")
    parser.add_argument(
        "-s",
        "--salt",
        dest="salt",
        type=str,
        required=False,
        default="1234",
        help="Cluster salt number for a proper identification",
    )
    parser.add_argument(
        "-i",
        "--input",
        dest="input_folder",
        type=utils.PathType(verify_exist=True, create=False),
        required=True,
        help="Input folder of file to obfuscate",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_folder",
        type=utils.PathType(verify_exist=False, create=False),
        required=False,
        help="Output folder to save obfuscated files",
    )
    parser.add_argument(
        "-w",
        "--workers",
        dest="workers",
        type=utils.IntRange(imin=1),
        default=None,  # decided by pool type class
        required=False,
        help="Number of files to obfuscate in parallel.",
    )
    parser.add_argument(
        "--strategy",
        dest="strategy",
        choices=StrategyTypes.names(),
        type=str,
        required=False,
        default=StrategyTypes.HYBRID.value,
        help="Strategy to run",
    )
    parser.add_argument(
        "-m",
        "--min-split-size-in-bytes",
        dest="min_split_size_in_bytes",
        type=utils.IntRange(imin=1),
        required=False,
        default=SIZE_TO_SPLIT_IN_BYTES,
        help="Minimum file size to split, in bytes",
    )
    parser.add_argument(
        "-rm",
        "--remove-original",
        dest="remove_original",
        action="store_true",
        required=False,
        help="Remove original file after obfuscation",
    )
    parser.add_argument(
        "-log",
        "--log-folder",
        dest="log_folder",
        type=utils.PathType(verify_exist=not test, create=True),
        required=False,
        help="Log file folder",
    )
    parser.add_argument(
        "--ignore-hint",
        dest="ignore_hint",
        type=str,
        required=False,
        help="Ignore file hint regex: Checks first line",
    )
    parser.add_argument(
        "-t",
        "--measure-time",
        dest="measure_time",
        default=False,
        action="store_true",
        required=False,
        help="Measure obfuscation times",
    )
    parser.add_argument(
        "--pool-type",
        dest="pool_type",
        choices=thread_pool_choices,
        default=None,
        required=False,
        help=f"Choose concurrency pool: {thread_pool_choices}.\nDefault pool: {default_pool}",
    )
    parser.add_argument(
        "--threshold",
        dest="threshold",
        default=200,
        required=False,
        type=utils.IntRange(imin=1),
        help="Threshold to try next obfuscator",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        default=False,
        required=False,
        action="store_true",
        help="Explain what is being done",
    )
    parser.add_argument(
        "--debug",
        dest="debug",
        default=False,
        required=False,
        action="store_true",
        help="Debug mode: no parallel obfuscation",
    )
    parser.add_argument(
        "--debug-prints",
        dest="debug_prints",
        default=False,
        required=False,
        action="store_true",
        help="Debug mode: Add debug prints",
    )
    parser.add_argument(
        "--replacer",
        default="sed -i",
        required=False,
        help="sed argument: sed -i, perl -pi.bak -e",
    )
    parser.add_argument(
        "--searcher",
        default="rg -ioe",
        required=False,
        help="grep argument: grep -Ewo, grep -Pwo",
    )
    parser.add_argument(
        "--sorter", default="sort -u", required=False, help="sort argument: sort -u"
    )
    parser.add_argument(
        "--ripgrep-path",
        default=None,
        required=False,
        help="path to ripgrep. Default use default rg",
    )
    return parser


def main():
    parser = get_args_parser()
    args = parser.parse_args()
    utils.init_logger(args)
    utils.logger.debug(f"args: {args.__dict__}")
    strategy_obj = OBFUSCATION_METHODS_FACTORY[StrategyTypes(args.strategy)](args=args)
    utils.logger.info(strategy_obj)

    strategy = (
        utils.measure_time(strategy_obj.run) if args.measure_time else strategy_obj.run
    )
    return strategy()


if __name__ == "__main__":
    sys.exit(main())
