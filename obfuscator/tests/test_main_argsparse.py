from ..lib.enums import StrategyTypesEnum
from ..main import get_args_parser

utils_kwargs = {"log_to_debug": False}
DUMMY_SALT = "1234"
TEMP_DIR = "/tmp/"
MINIMUM_GOOD_CMD = f"-i {TEMP_DIR} -o {TEMP_DIR} -s {DUMMY_SALT}"  # DO NOT CHANGE
parser = get_args_parser()


def test_args_default():
    kwargs = {
        "input_folder": TEMP_DIR,
        "output_folder": TEMP_DIR,
        "salt": DUMMY_SALT,
        "log_folder": TEMP_DIR,
        "verbose": False,
        "workers": None,
        "strategy": StrategyTypesEnum.HYBRID.value,
        "ignore_hint": None,
        "measure_time": True,
        "pool_type": None,
    }
    args_cmd = f"{MINIMUM_GOOD_CMD} --log-folder {TEMP_DIR}"
    parsed_args = parser.parse_args(args_cmd.split(" "))

    list_err = []
    for arg, expected_res in kwargs.items():
        arg_val = getattr(parsed_args, arg)
        if arg_val != expected_res:
            list_err.extend(
                [f"Case: {args_cmd}", f"==> Failed with args: {arg}-> expected: '{expected_res}' <=="]
            )

    if list_err:
        raise AssertionError("\n".join(list_err))


def test_args_must_fail():
    list_err = []
    for args in [
        "",  # empty
        f"{MINIMUM_GOOD_CMD} -V",  # -V is not supported
        f"{MINIMUM_GOOD_CMD} --workers 8.5",  # invalid workers type
        f"{MINIMUM_GOOD_CMD} --workers -4",  # invalid workers type
        f"{MINIMUM_GOOD_CMD} --workers 0",  # invalid workers number
        f"{MINIMUM_GOOD_CMD} --strategy popo",  # no such strategy
        f"{MINIMUM_GOOD_CMD} -m 0",  # invalid min_split
        f"{MINIMUM_GOOD_CMD} -m -4",  # invalid min_split
    ]:
        try:
            parser.parse_args(args.split(" "))
            list_err.append(f"failed with args: {args}")
        except SystemExit as e:
            if str(e) != "2":
                list_err.append(f"failed with args: {args}")
    if list_err:
        raise AssertionError("\n".join(list_err))


def test_folder_not_exist():
    for cmd in [
        f"-i /_no_way_this_folder_exist -o /out --salt 120 --log_folder {TEMP_DIR}",
        f"-i {TEMP_DIR} -o /out --salt 120 --log_folder /__no_way_this_folder_exist",
    ]:
        try:
            parser.parse_args(cmd.split(" "))
        except SystemExit as e:
            assert str(e) == "2"
