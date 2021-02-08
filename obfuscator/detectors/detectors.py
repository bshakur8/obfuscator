import hashlib
import re
from functools import lru_cache

from scrubadub.detectors.base import RegexDetector
from scrubadub.filth import RegexFilth


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

    @staticmethod
    def _hash_data(data):
        # Constant hash between different servers
        return hashlib.md5(str(data).encode()).hexdigest()

    @property
    @lru_cache(1)
    def _const_hash(self):
        return self._hash_data("".join((str(x) for x in (self.type, self.salt))))

    @property
    def hash(self):
        return self._hash_data(f"{self._const_hash}{self.text.lower()}")

    @property
    def identifier(self):
        i = self.lookup[self.hash]
        return u'%s-%s' % (self.placeholder, i)

    def replace_with(self, **kwargs):
        return self.prefix + self.identifier + self.suffix


class PortFilth(AbsObfuscatorFilth):
    type = 'port'
    regex = re.compile(r"(port\s*[#=:>-]\s*\d+)", re.IGNORECASE | re.MULTILINE)


class IPv4Filth(AbsObfuscatorFilth):
    type = 'ip:port'
    # valid: IP:port, IP/subnet
    # 555.11.516.9910101 is not a valid IP
    regex = re.compile(
        r"""\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b([:\\]\s*\d+)?""",
        re.IGNORECASE | re.MULTILINE)


class FilesDirFilth(AbsObfuscatorFilth):
    type = "file_dir"
    regex = re.compile(r"\B/[^ :\t\n]+\b", re.IGNORECASE | re.MULTILINE)


class MACFilth(AbsObfuscatorFilth):
    type = "mac_addr"
    regex = re.compile("([0-9a-fA-F]{2}[:]){5}([0-9a-fA-F]{2})", re.IGNORECASE | re.MULTILINE)


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


class ObfuscatorLookup:
    """The Lookup object is used to create an in-memory reference table to
    create unique identifiers for ``Filth`` that is encountered.
    Unlike scrubadub Lookup that takes that next index, Obfuscator lookup
    takes the first # of the hashkey which is constant among all servers
    """

    def __init__(self, collection):
        self.table = collection if collection is not None else {}

    def __getitem__(self, key):
        try:
            return self.table[key]
        except KeyError:
            self.table[key] = key[:5]
            return self.table[key]
