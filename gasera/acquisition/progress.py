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
        # percent: progress within current logical unit (repeat/cycle) 0..100
        self.percent = 0

        # overall_percent: mux -> across all repeats 0..100
        # motor -> typically mirrors percent (unbounded run)
        self.overall_percent = 0
        self.repeat_index = 0

        # step_index: total completed measurements (monotonic count; mux sets deterministically)
        self.step_index: int = 0

        self.elapsed_seconds = 0.0
        # repeat_total/total_steps/tt_seconds are set by engine on start
        
    def reset_all(self):
        """Reset all progress state."""
        self.reset_runtime()
        self.repeat_total = 0
        self.total_steps = 0
        self.enabled_count = 0
        self.tt_seconds = None

    def to_dict(self) -> dict:
        return dict(self.__dict__)
