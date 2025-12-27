# system/display_state.py

from dataclasses import dataclass
from typing import Optional, Literal

DisplayMode = Literal[
    "idle",     # nothing running
    "armed",    # motor started, waiting for trigger
    "running",  # active measurement
    "done",     # task finished (summary)
    "error",    # aborted / fault
    "info",     # short informational screen
]


@dataclass
class DisplayState:
    # High-level display intent
    mode: DisplayMode

    # Main text
    title: str
    subtitle: Optional[str] = None

    # Timing (display-ready)
    et_seconds: Optional[float] = None
    tt_seconds: Optional[float] = None

    # Step / progress info (display-ready)
    step_current: Optional[int] = None
    step_total: Optional[int] = None

    # Footer line (IP, clock, warnings, etc.)
    footer: Optional[str] = None

    # Timed screen support
    ttl_seconds: Optional[float] = None     # auto-expire after N seconds
    return_to: Optional[DisplayMode] = None # where to go after ttl
