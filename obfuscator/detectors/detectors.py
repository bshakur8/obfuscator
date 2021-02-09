import re
from functools import lru_cache

from scrubadub.detectors.base import RegexDetector
from scrubadub.filth import RegexFilth

from strategy import utils


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
        return utils.hash_string("".join((str(x) for x in (self.type, self.salt))))

    def replace_with(self, **kwargs):
        return self.prefix + \
               u'%s-%s' % (self.placeholder, utils.hash_string(f"{self._const_hash}{self.text.lower()}")) \
               + self.suffix


class LowLevelFilth:

    def __init__(self, salt, placeholder, regex):
        self.salt = salt
        self.placeholder = placeholder
        self.regex = regex

    def __str__(self):
        return f"{self.placeholder}"

    def __repr__(self):
        return self.__str__()

    @property
    @lru_cache(1)
    def _const_hash(self):
        return utils.hash_string("".join((str(x) for x in (self.placeholder, self.salt))))

    def replace_with(self, text):
        return u'{{' + u'%s-%s' % (self.placeholder, utils.hash_string(f"{self._const_hash}{text}")) + u"}}"


class PortFilth(AbsObfuscatorFilth):
    type = 'port'
    regex = re.compile(r"(port\s*[#=:>-]\s*\d+)", re.IGNORECASE | re.MULTILINE)


reg = r"""\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b([:\\]\s*\d+)?"""


class IPv4Filth(AbsObfuscatorFilth):
    type = 'ipv4'
    # valid: IP:port, IP/subnet
    # 555.11.516.9910101 is not a valid IP
    regex = re.compile(reg)


class FilesDirFilth(AbsObfuscatorFilth):
    type = "file-dir"
    regex = re.compile(r"\B/[^ :\t\n]+\b")


class MACFilth(AbsObfuscatorFilth):
    type = "mac-addr"
    regex = re.compile("([0-9a-fA-F]{2}[:]){5}([0-9a-fA-F]{2})")


class MyCredentialFilth(AbsObfuscatorFilth):
    type = "credentials"
    CREDENTIALS_KEYWORDS = [
        "username", "user", "login", "password", "pass",  # defaults
        "root_password", "root_username",  # root
        "ipmi_password", "ipmi_user",  # ipmi
        "ipmi_user_supermicro", "ipmi_password_supermicro",  # supermicro
        "ipmi_user_cascadelake", "ipmi_password_cascadelake",  # cascadelake
        "sudo_user", "vms_user", "ssh_user", "ssh_password",  # ssh
        "vms_db_user", "vms_db_pass", "db_user", "redis_pass",  # db
        "aws_ssh_user", "secret_key", "secret_key", "default_access_key_id", "default_secret_key_id",
        "default_support_access_key_id", "default_support_secret_key_id", "docker_registry",  # aws
        "mars_kafka_rest_password", "mars_kafka_rest_user",  # mars
        "admin_username", "admin_password", "admin_email", "support_username", "support_password"  # others
    ]
    keywords = "|".join(CREDENTIALS_KEYWORDS)
    regex_str = fr"\b(({keywords})([: =])+\S+)"
    regex = re.compile(regex_str, re.IGNORECASE | re.MULTILINE)


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
