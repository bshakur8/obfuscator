import unittest

from src.detectors.detectors import FilesDirFilth, IPv4Filth, MyCredentialFilth


class TestRegex(unittest.TestCase):

    def test_path_dir_success(self):
        list_cases = [
            "/"
            , "  /"  # tab
            , "       /"  # spaces
            , "/a"
            , "/a.tmp"
            , "/a/b/"
            , "/a/b/c.tmp"
            , "/a/b/c.x.y.z"
            , "/a/b/c.x.y.z              "  # spaces
            , "/a/b/c.x.y.z         "  # tabs
        ]

        self.check_errors(compiled_regex=FilesDirFilth.regex, list_cases=list_cases,
                          fail_criteria=lambda m: m is None,
                          string_format="FileDir {}")

    def test_path_dir_failure(self):
        list_cases = [
            ""
            , "a"
            , "a.tmp"
            , "a/b/"
            , "a/b/c.tmp"

        ]
        self.check_errors(compiled_regex=FilesDirFilth.regex, list_cases=list_cases,
                          fail_criteria=lambda m: m is not None,
                          string_format="FileDir {}")

    def test_credentials_success(self):
        list_cases = [
            "username admin"
            , "username:admin"
            , "username :admin"
            , "username : admin"
            , "username= admin"
            , "username= admin password: 1245"
            , "username= admin password: 1245             "
            , "             username= admin password: 1245             "

        ]
        self.check_errors(compiled_regex=MyCredentialFilth.regex, list_cases=list_cases,
                          fail_criteria=lambda m: m is None,
                          string_format="Credentials {}")

    def test_credentials_failure(self):
        list_cases = [
            "usernameadmin"
            , "username-admin"
            , "username(admin)"

        ]
        self.check_errors(compiled_regex=MyCredentialFilth.regex, list_cases=list_cases,
                          fail_criteria=lambda m: m is not None,
                          string_format="Credentials {}")

    def test_ip_regex_success(self):

        list_cases = [
            "10.20.30.40",
            "10.20.30.40:8080",
            "\t10.20.32.34",
            " 10.20.32.34",
            "        10.20.32.34",
            "        10.20.32.34           ",
            "10.20.30.40 port 8080",
            "        1.2.32.34:56:78:90", ]

        self.check_errors(compiled_regex=IPv4Filth.regex, list_cases=list_cases,
                          fail_criteria=lambda m: m is None,
                          string_format="IP {}")

    def test_ip_regex_failure(self):

        list_cases = ["10.20.30.40.5.6.7.8",
                      "10.20.30.40::56",
                      "1.2.3.4.",
                      "1.2.3.4port123",
                      "1.2.3.4port 123",
                      "1.2.3.4: 123",
                      ]

        self.check_errors(compiled_regex=IPv4Filth.regex, list_cases=list_cases,
                          fail_criteria=lambda m: m is not None,
                          string_format="IP {}")

    def check_errors(self, compiled_regex, list_cases, fail_criteria, string_format):
        dict_errs = {}

        for idx, obj in enumerate(list_cases):
            m = compiled_regex.search(obj)
            if fail_criteria(m):
                s = string_format.format(obj)
                dict_errs[obj] = f"[index={idx}]: {s}"

        self.assertEqual(len(dict_errs), 0,
                         "Found errors: {}".format("\n".join([f"{v}" for k, v in dict_errs.items()])))
