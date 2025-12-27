# gasera/acquisition/display_event.py

from enum import Enum, auto


class DisplayEvent(Enum):
    """
    Discrete, semantic UI-relevant moments emitted by engines.
    NOT continuous state.
    NOT screens.
    """
    ENGINE_STARTED = auto()

    WAITING_FOR_TRIGGER = auto()   # motor armed, waiting user
    CYCLE_STARTED = auto()
    CYCLE_FINISHED = auto()

    TASK_FINISHED = auto()         # user ended task normally
    TASK_ABORTED = auto()          # aborted by user or error

    ERROR = auto()                 # unrecoverable error
