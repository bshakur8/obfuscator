from ..lib.detectors import FilesDirFilth, CredentialFilth, IPv4Filth


def test_path_dir_success():
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

    check_errors(
        compiled_regex=FilesDirFilth.regex,
        cases=cases,
        fail_criteria=lambda m: m is None,
        filth_type="FileDir",
    )


def test_path_dir_failure():
    cases = ["", "a", "a.tmp", "a/b/", "a/b/c.tmp"]
    check_errors(
        compiled_regex=FilesDirFilth.regex,
        cases=cases,
        fail_criteria=lambda m: m is not None,
        filth_type="FileDir",
    )


def test_credentials_special_keywords_success():
    cases = []
    for keyword in CredentialFilth.CREDENTIALS_KEYWORDS:
        for space in (" ", ""):
            for op in (":", "=", " "):
                cases.append(f"{keyword}{space}{op}{space}123")

    check_errors(
        compiled_regex=CredentialFilth.regex,
        cases=cases,
        fail_criteria=lambda m: m is None,
        filth_type="Credentials",
    )


def test_credentials_success():
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
    check_errors(
        compiled_regex=CredentialFilth.regex,
        cases=cases,
        fail_criteria=lambda m: m is None,
        filth_type="Credentials",
    )


def test_credentials_failure():
    cases = ["usernameadmin", "username-admin", "username(admin)"]
    check_errors(
        compiled_regex=CredentialFilth.regex,
        cases=cases,
        fail_criteria=lambda m: m is not None,
        filth_type="Credentials",
    )


def test_ip_regex_success():
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

    check_errors(
        compiled_regex=IPv4Filth.regex,
        cases=cases,
        fail_criteria=lambda m: m is None,
        filth_type="IP",
    )


def test_ip_regex_failure():
    cases = [
        "502.1410.30.40.5.651.7.8",
        "10.20:30.40::56",
        "1.2..3.4.",
        "1.2.3.4port123",
        "1.2.3.4port 123",
        "1-2-3-4",
    ]

    check_errors(
        compiled_regex=IPv4Filth.regex,
        cases=cases,
        fail_criteria=lambda m: m is not None,
        filth_type="IP",
    )


def check_errors(compiled_regex, cases, fail_criteria, filth_type):
    dict_errs = {}

    for idx, obj in enumerate(cases):
        m = compiled_regex.search(obj)
        if fail_criteria(m):
            dict_errs[obj] = f"[index={idx}]: {filth_type} {obj}"

    assert len(dict_errs) == 0, "Found errors: {}".format("\n".join([f"{v}" for k, v in dict_errs.items()]))
