import unittest

from detectors.detectors import FilesDirFilth, IPv4Filth, MyCredentialFilth


class TestRegex(unittest.TestCase):
    def test_path_dir_success(self):
        cases = [
            "  /popo",
            "       /momo",
            "/a",
            "/a.tmp",
            "/a/b/",
            "/a/b/c.tmp",
            "/a/b/c.x.y.z",
            "/a/b/c.x.y.z              ",
            "/a/b/c.x.y.z         ",
        ]

        self.check_errors(
            compiled_regex=FilesDirFilth.regex,
            cases=cases,
            fail_criteria=lambda m: m is None,
            string_format="FileDir {}",
        )

    def test_path_dir_failure(self):
        cases = ["", "a", "a.tmp", "a/b/", "a/b/c.tmp"]
        self.check_errors(
            compiled_regex=FilesDirFilth.regex,
            cases=cases,
            fail_criteria=lambda m: m is not None,
            string_format="FileDir {}",
        )

    def test_credentials_special_keywords_success(self):
        cases = []
        for keyword in MyCredentialFilth.CREDENTIALS_KEYWORDS:
            for space in (" ", ""):
                for op in (":", "=", " "):
                    cases.append(f"{keyword}{space}{op}{space}123")

        self.check_errors(
            compiled_regex=MyCredentialFilth.regex,
            cases=cases,
            fail_criteria=lambda m: m is None,
            string_format="Credentials {}",
        )

    def test_credentials_success(self):
        cases = [
            "username admin",
            "username:admin",
            "username :admin",
            "username : admin",
            "username= admin",
            "username= admin password: 1245",
            "username= admin password: 1245             ",
            "             username= admin password: 1245             ",
        ]
        self.check_errors(
            compiled_regex=MyCredentialFilth.regex,
            cases=cases,
            fail_criteria=lambda m: m is None,
            string_format="Credentials {}",
        )

    def test_credentials_failure(self):
        cases = ["usernameadmin", "username-admin", "username(admin)"]
        self.check_errors(
            compiled_regex=MyCredentialFilth.regex,
            cases=cases,
            fail_criteria=lambda m: m is not None,
            string_format="Credentials {}",
        )

    def test_ip_regex_success(self):

        cases = [
            "10.20.30.40",
            "10.20.30.40:8080",
            "\t10.20.32.34",
            " 10.20.32.34",
            "        10.20.32.34",
            "        10.20.32.34           ",
            "10.20.30.40",
            "        1.2.32.34:56:78:90",
        ]

        self.check_errors(
            compiled_regex=IPv4Filth.regex,
            cases=cases,
            fail_criteria=lambda m: m is None,
            string_format="IP {}",
        )

    def test_ip_regex_failure(self):

        cases = [
            "502.1410.30.40.5.651.7.8",
            "10.20:30.40::56",
            "1.2..3.4.",
            "1.2.3.4port123",
            "1.2.3.4port 123",
            "1-2-3-4",
        ]

        self.check_errors(
            compiled_regex=IPv4Filth.regex,
            cases=cases,
            fail_criteria=lambda m: m is not None,
            string_format="IP {}",
        )

    def check_errors(self, compiled_regex, cases, fail_criteria, string_format):
        dict_errs = {}

        for idx, obj in enumerate(cases):
            m = compiled_regex.search(obj)
            if fail_criteria(m):
                s = string_format.format(obj)
                dict_errs[obj] = f"[index={idx}]: {s}"

        self.assertEqual(
            len(dict_errs),
            0,
            "Found errors: {}".format(
                "\n".join([f"{v}" for k, v in dict_errs.items()])
            ),
        )
