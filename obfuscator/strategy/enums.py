from enum import Enum


class RCEnum(Enum):
    SUCCESS = 0
    IGNORED = 1
    FAILURE = 2


class Segments(Enum):
    FILE_DIR = "FILE"
    CREDENTIALS = "CRED"
    MAC_ADDR = "MAC"
    IP = "IP"
