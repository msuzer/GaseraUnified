# system/display_state.py

from dataclasses import dataclass
from typing import List, Optional, Literal

ScreenType = Literal[
    "idle",     # nothing running
    "armed",    # motor started, waiting for trigger
    "running",  # active measurement
    "summary",  # task finished (summary)
    "error",    # aborted / fault
    "info",     # short informational screen
]


@dataclass
class DisplayState:
    screen: ScreenType
    header: str
    lines: List[str]

    ttl_seconds: Optional[float] = None
    return_to: Optional[ScreenType] = None
