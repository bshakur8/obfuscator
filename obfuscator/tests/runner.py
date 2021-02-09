#!/usr/bin/env python3
import os

from strategy import utils
from strategy.enums import StrategyTypes

# infile = "/tmp/test_bundle_obf/files/f_2GB"
from strategy.workers_pool import WorkersPool

infile = "/tmp/test_bundle_obf/files/f_86M"
# infile = "/tmp/test_bundle_obf/files/f_14M"
# infile = "/tmp/test_bundle_obf/files/f_161K"
results_folder = "/tmp/test_bundle_obf/results"
logs_folder = "/tmp/test_bundle_obf/log"

min_size_to_split = 4 * 1024 ** 2  # 4 MB
workers = 30
defaults = f"-w {workers} -m {min_size_to_split} -v -t -s 1234"


def pre():
    os.system(f"rm -rf {logs_folder}")  # remove old
    os.system(f"rm -rf {results_folder}")
    os.system(f"mkdir -p {logs_folder}")  # create new
    os.system(f"mkdir -p {results_folder}")


def sam_test():
    strategy_name = StrategyTypes.SAM.value
    utils.logger.info("Main runner")

    for pool in WorkersPool:
        pool_type = pool.__name__
        run_name = f"{pool_type}_{strategy_name}"

        log_folder = os.path.join(logs_folder, run_name)
        os.system(f"mkdir -p {log_folder}")
        result_file = os.path.join(results_folder, run_name)

        args = f"--strategy {strategy_name} --pool-type {pool_type} -log {log_folder} -i {infile} -o {result_file} {defaults}"
        run_test(run_name=run_name, log_folder=log_folder, args=args)


def inplace_test():
    strategy_name = StrategyTypes.IN_PLACE.value
    run_name = f"run_{strategy_name}"

    # config log and result file
    log_folder = os.path.join(logs_folder, run_name)
    os.system(f"mkdir -p {log_folder}")
    result_file = os.path.join(results_folder, run_name)

    # Copy infile and create a new file to run with
    file_parse = f"{infile}_{run_name}"
    utils.logger.info(f"file_parse: {file_parse}")
    os.system(f"rm -rf {file_parse}")  # Remove any old file
    os.system(f"cp {infile} {file_parse}")  # Create a new copy

    args = f"--strategy {strategy_name} -log {log_folder} -i {file_parse} -o {result_file} {defaults}"
    run_test(run_name=run_name, log_folder=log_folder, args=args)


def run_test(run_name, log_folder, args):
    utils.logger.info(f"Run {run_name} ==> {log_folder}")
    try:
        utils.run_local_cmd(f"python main.py {args}")
    except Exception:
        utils.logger.exception(f"Exception during to run Pool type: {run_name}")
    finally:
        utils.logger.info("{0}END - {1}{0}".format('-' * 10, run_name))


def tester():
    sam_test()
    inplace_test()


def main():
    pre()
    tester()


if __name__ == '__main__':
    main()
