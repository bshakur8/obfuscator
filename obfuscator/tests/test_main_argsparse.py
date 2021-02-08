from unittest import TestCase

from main import get_args_parser, IN_PLACE

utils_kwargs = {"log_to_debug": False}

FOUND_FOLDER = "/tmp"
DUMMY_SALT = "1234"


class TestMain(TestCase):
    MINIMUM_GOOD_CMD = f"-i {FOUND_FOLDER} -o {FOUND_FOLDER} -s {DUMMY_SALT}"  # DO NOT CHANGE

    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = get_args_parser()

    def test_args_defaults(self):
        kwargs = {"input_folder": "/tmp/",
                  "output_folder": "/tmp/",
                  "salt": DUMMY_SALT,
                  "log_folder": "/tmp/",
                  "verbose": False,
                  "workers": None,
                  "strategy": IN_PLACE,
                  "ignore_hint": None,
                  "measure_time": False,
                  "pool_type": None,
                  "remove_original": False
                  }
        args_cmd = f"{self.MINIMUM_GOOD_CMD} --log-folder /tmp"
        parsed_args = self.parser.parse_args(args_cmd.split(" "))

        list_err = []
        for arg, expected_res in kwargs.items():
            if getattr(parsed_args, arg) != expected_res:
                list_err.append(f"=======> Failed with args: {arg}-> expected: '{expected_res}' <=======."
                                f"Case: {args_cmd}")

        if list_err:
            raise AssertionError("\n".join(list_err))


def test_args_must_fail(self):
    list_err = []
    for args in [
        "",  # empty
        "-i /tmp",  # missing -s -o
        "-i /tmp -o /tmp -log /_stam_folder_",  # -log is not found
        f"{self.MINIMUM_GOOD_CMD} -V",  # -V is not supported
        f"{self.MINIMUM_GOOD_CMD} --workers 8.5",  # invalid workers type
        f"{self.MINIMUM_GOOD_CMD} --workers -4",  # invalid workers type
        f"{self.MINIMUM_GOOD_CMD} --workers 0",  # invalid workers number
        f"{self.MINIMUM_GOOD_CMD} -s {'5678'}",  # bad salt
        f"{self.MINIMUM_GOOD_CMD} --strategy popo",  # no such strategy
        f"{self.MINIMUM_GOOD_CMD} -m 0",  # invalid min_split
        f"{self.MINIMUM_GOOD_CMD} -m -4",  # invalid min_split
    ]:
        try:
            _ = self.parser.parse_args(args.split(" "))
            list_err.append(f"failed with args: {args}")
        except SystemExit as e:
            if str(e) != "2":
                list_err.append(f"failed with args: {args}")

    if list_err:
        raise AssertionError("\n".join(list_err))


def test_folder_not_exist(self):
    for cmd in ["-i /_no_way_this_folder_exist -o /out --salt 120 --log_folder /tmp",
                "-i /tmp -o /out --salt 120 --log_folder /__no_way_this_folder_exist"]:
        try:
            _ = self.parser.parse_args(cmd.split(" "))
        except SystemExit as e:
            self.assertEqual(str(e), "2")
