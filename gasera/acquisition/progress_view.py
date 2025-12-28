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
    def channel_step_label(self) -> Optional[str]:
        if self.p is None or self.p.current_channel is None or self.p.step_index is None:
            return None

        has_total_steps = self.p.total_steps is not None and self.p.total_steps > 0

        current_step = self.p.step_index + 1        
        if has_total_steps:
            current_step = min(current_step, self.p.total_steps) # cap it to total_steps if known
            step_str = f"Step {current_step}/{self.p.total_steps}"
        else:
            step_str = f"Step {current_step}"
        
        return f"Ch{self.p.current_channel + 1} {step_str}"

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
