from enum import Enum


class LogType(Enum):
    INFO = 1
    WARN = 2
    ERROR = 3
    AGENT_MESSAGE = 4
    AGENT_REASONING = 5
