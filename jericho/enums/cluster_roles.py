from enum import Enum


class ClusterRole(Enum):
    MASTER = "master"
    SLAVE = "slave"
    DISABLED = "disabled"
