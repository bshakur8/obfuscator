from enum import Enum


class StrategyTypes(Enum):
    IN_PLACE = "in_place"
    SAM = "split_merge"
    SAP = "split_in_place"
    LOW_LEVEL = "low_level"
    HYBRID = "hybrid"
    HYBRID_SPLIT = "hybrid_split"
    RIPGREP = "ripgrep"

    @classmethod
    def names(cls):
        return [str(v.value) for v in cls._value2member_map_.values()]


class RCEnum(Enum):
    SUCCESS = 0
    IGNORED = 1
    FAILURE = 2


class Segments(Enum):
    FILE_DIR = "FILE"
    CREDENTIALS = "CRED"
    MAC_ADDR = "MAC"
    IP = "IP"
