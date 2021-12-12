from enum import Enum, unique


@unique
class LinkPrefixes(Enum):
    MAIL = "mailto:"
    PHONE = "tel:"