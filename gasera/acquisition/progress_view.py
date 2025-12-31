# gasera/acquisition/progress_view.py

from dataclasses import dataclass
from typing import Optional
from gasera.acquisition.progress import Progress
from system.utils import format_duration, format_consistent_pair

@dataclass(frozen=True)
class ProgressView:
    p: Progress

    # -----------------------------
    # Channels / Steps
    # -----------------------------
    @property
    def get_step_string(self) -> Optional[str]:
        if self.p is None or self.p.step_index is None:
            return None

        has_total_steps = self.p.total_steps is not None and self.p.total_steps > 0
        # `step_index` represents the number of completed measurements.
        # self.progress.step_index = repeat_index * self.progress.enabled_count + steps_completed_in_single_repeat
        completed = self.p.repeat_index * self.p.enabled_count + self.p.step_index
        if has_total_steps:
            completed = min(completed, self.p.total_steps)
            step_str = f"{completed}/{self.p.total_steps}"
        else:
            step_str = f"{completed}"

        return step_str
    
    @property
    def step_done_label(self) -> Optional[str]:
        step_str = self.get_step_string
        if step_str is None:
            return None

        return f"Done: {step_str} steps"

    @property
    def channel_step_label(self) -> Optional[str]:
        if self.p is None or self.p.current_channel is None or self.p.step_index is None:
            return None

        step_str = self.get_step_string
        if step_str is None:
            return None
        
        return f"Ch{self.p.current_channel + 1} Step {step_str}"

    # -----------------------------
    # Duration
    # -----------------------------
    @property
    def duration_label(self) -> Optional[str]:
        if self.p is None or self.p.elapsed_seconds is None:
            return None
    
        has_total_duration = self.p.tt_seconds is not None and self.p.tt_seconds > 0

        elapsed = self.p.elapsed_seconds
        total = self.p.tt_seconds
        if has_total_duration:
            elapsed = min(elapsed, total) # cap to tt_seconds if known
            et_str, tt_str = format_consistent_pair(elapsed, total)
            duration_str = f"D: {et_str}/{tt_str}"
        else:
            et_str = format_duration(elapsed, fixed=True)
            duration_str = f"D: {et_str}"

        return duration_str

    # -----------------------------
    # Phase
    # -----------------------------
    @property
    def phase_label(self) -> str:
        return f"> {self.p.phase}"
