import os
import shutil

from ..lib import utils
from ..lib.utils import obfuscate_in_place
from ..strategy.split_in_place import ObfuscateInplace


class DummyArgs:
    pass


utils.init_logger()
dir_name = os.path.dirname(__file__)
assert os.path.exists(dir_name)
obfuscate_folder = f"{dir_name}/logs_dir/"
assert os.path.exists(obfuscate_folder)


def get_args():
    args = DummyArgs()
    args.pool_type = "multiprocess"
    args.workers = 1
    args.salt = "1234"
    args.serially = True
    args.ignore_hint = None
    args.min_split_size_in_bytes = 1 * 1024**2
    args.output_folder = os.path.join(obfuscate_folder, "after")
    args.input_folder = os.path.join(obfuscate_folder, "ip_addr.log")
    args.verbose = True
    return args


def _get_files(args):
    if os.path.isdir(args.input_folder):
        raw_files = [os.path.join(args.input_folder, f) for f in os.listdir(args.input_folder)]
        files = utils.clone_folder(raw_files, args)
    elif os.path.isfile(args.input_folder):
        new_file = utils.clone_file_path(args.input_folder, target_dir=args.output_folder)
        shutil.copyfile(args.input_folder, new_file)
        files = [new_file]
    else:
        assert False, f"args.input_folder={args.input_folder}"
    utils.logger.info(f"files={files}")
    return files


def test_sanity():
    args = get_args()
    files = _get_files(args=args)

    result_file = files[0]
    utils.logger.info(f"result_file={result_file}")
    try:
        obfuscator = ObfuscateInplace(args)
        obfuscator.run()

        with open(result_file) as fd:
            content = fd.readlines()

        errs = []
        for segment in [
            "{{IPV4-8341c}}",
            "{{MAC-ADDR-72994}}",
            "{{MAC-ADDR-6de52}",
            "{IPV4-25bee}}",
        ]:
            for line in content:
                if segment in line:
                    break
            else:
                errs.append(f"segment: {segment} not in obfuscated file")

        assert errs == []
    finally:
        try:
            shutil.rmtree(args.output_folder)
        except NotADirectoryError:
            pass


def _test_inplace():
    args = get_args()
    obfuscator = ObfuscateInplace(args)
    f = f"{obfuscate_folder}ip_addr.log"
    obfuscate_in_place(f, obfuscator.scrubber)
