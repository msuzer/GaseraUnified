from typing import Optional
from gasera.acquisition.phase import Phase

class Progress:
    """
    Frontend contract (keep stable).
    Snapshot-safe: do NOT add non-serializable fields.
    """
    def __init__(self):
        self.reset_all()

    def reset_runtime(self):
        """Reset progress state for a new run."""
        self.phase = Phase.IDLE
        self.current_channel = 0
        self.next_channel = None
        self.percent = 0
        self.overall_percent = 0
        self.repeat_index = 0
        self.step_index: int = 0
        self.elapsed_seconds = 0.0

    def reset_all(self):
        self.reset_runtime()
        self.repeat_total = 0
        self.total_steps = 0
        self.enabled_count = 0
        self.tt_seconds = None
        self.duration_str: Optional[str] = None
        self.progress_str: Optional[str] = None

    def to_dict(self) -> dict:
        return dict(self.__dict__)
