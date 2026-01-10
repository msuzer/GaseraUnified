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
    def _format_steps(self, completed: Optional[int]) -> Optional[str]:
        if completed is None:
            return None

        total = self.p.total_steps
        if total is not None and total > 0:
            return f"{min(completed, total)}/{total}"

        return f"{completed}"

    @property
    def mux_completed_steps_str(self) -> Optional[str]:
        if (self.p.step_index is None or self.p.repeat_index is None or self.p.enabled_count is None):
            return None

        completed = self.p.repeat_index * self.p.enabled_count + self.p.step_index
        return self._format_steps(completed)

    @property
    def motor_completed_steps_str(self) -> Optional[str]:
        if self.p.step_index is None:
            return None

        completed = self.p.step_index # motor do not use repeats for steps
        return self._format_steps(completed)

    @property
    def mux_step_label(self) -> Optional[str]:
        return f"{self.mux_completed_steps_str} step(s)"

    @property
    def motor_repeat_label(self) -> Optional[str]:
        if self.p.repeat_total is None:
            return None
        
        return f"{self.p.repeat_total} repeat(s)"

    def _channel_label(self, step_str: Optional[str]) -> Optional[str]:
        if self.p.current_channel is None or step_str is None:
            return None
        return f"Ch{self.p.current_channel + 1}, {step_str} step(s)"

    @property
    def mux_channel_step_label(self) -> Optional[str]:
        step_str = self.mux_completed_steps_str
        return self._channel_label(step_str)

    @property
    def motor_channel_step_label(self) -> Optional[str]:
        step_str = self.motor_completed_steps_str
        return self._channel_label(step_str)

    # -----------------------------
    # Duration
    # -----------------------------
    @property
    def duration_label(self) -> Optional[str]:
        if self.p.elapsed_seconds is None:
            return None

        if self.p.tt_seconds and self.p.tt_seconds > 0:
            et, tt = format_consistent_pair(
                min(self.p.elapsed_seconds, self.p.tt_seconds),
                self.p.tt_seconds,
            )
            return f"{et}/{tt}"

        return format_duration(self.p.elapsed_seconds, fixed=True)
