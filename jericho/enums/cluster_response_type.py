from enum import Enum


class ClusterResponseType(Enum):
    FINISHED = "FINISHED"
    STATISTICS = "STATISTICS"
    RESULT = "RESULT"
    JOB = "JOB"
