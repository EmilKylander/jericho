from enum import Enum


class ClusterRole(Enum):
    SOURCE = "source"
    REPLICA = "replica"
    DISABLED = "disabled"
