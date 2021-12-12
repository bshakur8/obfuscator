import re
import uuid
from functools import lru_cache

from scrubadub.detectors.base import RegexDetector
from scrubadub.filth import RegexFilth

from obfuscator.strategy.enums import Segments


@lru_cache(100_000)
def hash_string(string):
    return str(uuid.uuid5(uuid.NAMESPACE_OID, string))[:8]


class _ObfDetectorsIterator:
    def __iter__(self):
        for d in IPv4Detector, FilesDirDetector, MACDetector, MyCredentialDetector:
            yield d

    @property
    def first(self):
        return IPv4Detector


ObfuscatorDetectors = _ObfDetectorsIterator()


class AbsObfuscatorFilth(RegexFilth):
    salt = None

    @property
    @lru_cache(1)
    def _const_hash(self):
        return hash_string("".join((str(x) for x in (self.type, self.salt))))

    def replace_with(self, **kwargs):
        string = "%s-%s" % (
            self.placeholder,
            hash_string(f"{self._const_hash}{self.text.lower()}"),
        )
        return self.prefix + string + self.suffix


class LowLevelFilth:
    def __init__(self, salt, placeholder, regex):
        self.salt = salt
        self.placeholder = placeholder
        self.regex = regex

    def __str__(self):
        return self.placeholder

    def __repr__(self):
        return self.__str__()

    @property
    @lru_cache(1)
    def _const_hash(self):
        return hash_string("".join((str(x) for x in (self.placeholder, self.salt))))

    def replace_with(self, text):
        _hash = hash_string(f"{self._const_hash}{text}")
        return "{{" + f"{self.placeholder}-{_hash}" + "}}"


class PortFilth(AbsObfuscatorFilth):
    REGEX = r"(port\s*[#=:>-]\s*\d+)"
    type = "port"
    regex = re.compile(REGEX, re.IGNORECASE | re.MULTILINE)


class IPv4Filth(AbsObfuscatorFilth):
    REGEX = r"""\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b([:\\]\s*\d+)?"""
    REGEX_2 = r"(25[0-5]|2[0-4][0-9]|[0-1]?[0-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|[0-1]?[0-9]?[0-9])){3}"
    type = Segments.IP.value
    # valid: IP:port, IP/subnet
    # 555.11.516.9910101 is not a valid IP
    regex = re.compile(REGEX)


class FilesDirFilth(AbsObfuscatorFilth):
    REGEX = r"\B/[^ :\t\n]+\b|\B/"
    type = Segments.FILE_DIR.value
    regex = re.compile(REGEX)


class MACFilth(AbsObfuscatorFilth):
    REGEX = r"([a-f0-9A-F]{2}[:]){5}[a-f0-9A-F]{2}"
    type = Segments.MAC_ADDR.value
    regex = re.compile(REGEX)


class MyCredentialFilth(AbsObfuscatorFilth):
    type = Segments.CREDENTIALS.value
    CREDENTIALS_KEYWORDS = [
        "username",
        "user",
        "login",
        "password",
        "pass",
        "root_password",
        "root_username",
        "ipmi_password",
        "ipmi_user",
        "ipmi_user_supermicro",
        "ipmi_password_supermicro",
        "ipmi_user_cascadelake",
        "ipmi_password_cascadelake",
        "sudo_user",
        "vms_user",
        "ssh_user",
        "ssh_password",
        "vms_db_user",
        "vms_db_pass",
        "db_user",
        "redis_pass",
        "aws_ssh_user",
        "secret_key",
        "secret_key",
        "default_access_key_id",
        "default_secret_key_id",
        "default_support_access_key_id",
        "default_support_secret_key_id",
        "docker_registry",
        "mars_kafka_rest_password",
        "mars_kafka_rest_user",
        "admin_username",
        "admin_password",
        "admin_email",
        "support_username",
        "support_password",
    ]
    keywords = "|".join(CREDENTIALS_KEYWORDS)
    REGEX = fr"\b(({keywords})([: =])+\S+)"
    regex = re.compile(REGEX, re.IGNORECASE | re.MULTILINE)


class PortDetector(RegexDetector):
    filth_cls = PortFilth


class IPv4Detector(RegexDetector):
    filth_cls = IPv4Filth


class MyCredentialDetector(RegexDetector):
    filth_cls = MyCredentialFilth


class MACDetector(RegexDetector):
    filth_cls = MACFilth


class FilesDirDetector(RegexDetector):
    filth_cls = FilesDirFilth
