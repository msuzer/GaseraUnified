# ============================================================
# MUX ENGINE
# ============================================================
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from gasera.acquisition.task_event import TaskEvent
from gasera.motion.iface import MotionInterface
from system.log_utils import debug, error, info, warn
from system import services

from gasera.acquisition.base import SWITCHING_SETTLE_TIME, BaseAcquisitionEngine
from gasera.acquisition.phase import Phase

from system.preferences import (
    KEY_MEASUREMENT_DURATION,
    KEY_PAUSE_SECONDS,
    KEY_REPEAT_COUNT,
    KEY_INCLUDE_CHANNELS,
    ChannelState,
)

@dataclass
class MuxTaskConfig:
    measure_seconds: int
    pause_seconds: int
    repeat_count: int
    include_channels: list[int] = field(default_factory=list)


class MuxAcquisitionEngine(BaseAcquisitionEngine):
    """
    Deterministic (configured channels + repeat_count).
    Refactor of your mux AcquisitionEngine into BaseAcquisitionEngine subclass.  :contentReference[oaicite:1]{index=1}
    """

    TOTAL_CHANNELS = 31

    def __init__(self, motion: MotionInterface):
        super().__init__(motion)
        self.cfg: Optional[MuxTaskConfig] = None

    def _start_ok_message(self) -> str:
        return "Measurement Task started"

    def _validate_and_load_config(self) -> tuple[bool, str]:
        prefs = services.preferences_service
        cfg = MuxTaskConfig(
            measure_seconds=int(prefs.get(KEY_MEASUREMENT_DURATION, 100)),
            pause_seconds=int(prefs.get(KEY_PAUSE_SECONDS, 5)),
            repeat_count=int(prefs.get(KEY_REPEAT_COUNT, 1)),
        )

        include_mask = prefs.get(KEY_INCLUDE_CHANNELS, [ChannelState.ACTIVE] * self.TOTAL_CHANNELS)
        cfg.include_channels = list(include_mask)
        self.cfg = cfg

        self.progress.enabled_count = sum(1 for s in cfg.include_channels if s > ChannelState.INACTIVE)
        if self.progress.enabled_count == 0:
            warn("[ENGINE] no channels enabled, skipping measurement")
            services.buzzer.play("invalid")
            return False, "No channels enabled"

        return True, "Configuration valid"

    def _on_start_prepare(self) -> tuple[bool, str]:
        assert self.cfg is not None

        ok, msg = self._start_measurement()
        if not ok:
            return False, msg

        # Frontend timing fields
        self.progress.repeat_total = self.cfg.repeat_count
        self.progress.total_steps = self.cfg.repeat_count * self.progress.enabled_count
        self.progress.tt_seconds = self.estimate_total_time_seconds()
        # set engine channel timeout for motion helpers
        self.channel_timeout_sec = SWITCHING_SETTLE_TIME
        
        self._emit_task_event(TaskEvent.TASK_STARTED)
        
        return True, "ok"

    def trigger_repeat(self) -> tuple[bool, str]:
        warn("[ENGINE] repeat_trigger not applicable for MUX project")
        return False, "repeat not supported for MUX project"

    def _run_loop(self) -> None:
        assert self.cfg is not None
        info(
            f"[ENGINE] start: measure={self.cfg.measure_seconds}s, pause={self.cfg.pause_seconds}s, "
            f"repeat={self.cfg.repeat_count}, enabled_channels={self.progress.enabled_count}/{self.TOTAL_CHANNELS}"
        )
                
        try:
            for rep in range(self.cfg.repeat_count):
                if self._stop_event.is_set():
                    break
                if not self._run_one_repeat(rep):
                    break
        finally:
            # nothing here; finalize in _finalize_run()
            pass

    def _run_one_repeat(self, rep: int) -> bool:
        assert self.cfg is not None

        overall_steps = self.progress.enabled_count * self.cfg.repeat_count
        processed = 0

        self.progress.percent = 0
        self.progress.current_channel = 0
        self.progress.next_channel = None
        self._refresh_derived_progress()

        # Home muxes at start of each repeat
        self.motion_home_and_wait()

        for vch, enabled in enumerate(self.cfg.include_channels):
            self.progress.current_channel = vch
            next_vch = vch + 1
            self.progress.next_channel = next_vch if next_vch < len(self.cfg.include_channels) else None
            self._refresh_derived_progress()

            if self._stop_event.is_set():
                return False

            if enabled > 0:
                if not self._measure_channel():
                    return False

                processed += 1
                self._update_progress(rep, processed, overall_steps)

            is_last_enabled = (processed >= self.progress.enabled_count)
            is_final_repeat = (rep + 1 >= self.cfg.repeat_count)

            if is_last_enabled:
                if is_final_repeat:
                    self._set_phase(Phase.SWITCHING)
                    self._blocking_wait(1.0, notify=True)
                    debug("[ENGINE] final channel of final repeat - signaled completion")
                    break
                debug("[ENGINE] all enabled channels processed for this repeat")
                break

            if not self.motion_move_and_wait(was_enabled=bool(enabled)):
                return False

        self.progress.repeat_index = rep + 1
        return True

    def _measure_channel(self) -> bool:
        assert self.cfg is not None

        self._set_phase(Phase.PAUSED)
        if not self._blocking_wait(self.cfg.pause_seconds, notify=True):
            return False

        self._set_phase(Phase.MEASURING)
        if not self._blocking_wait(self.cfg.measure_seconds, notify=True):
            warn("[ENGINE] Aborting: measurement interrupted")
            return False

        if self.check_gasera_stopped():
            warn("[ENGINE] Aborting: Gasera stopped unexpectedly")
            return False

        # Mark channel as sampled (memory only, no disk write)
        vch = self.progress.current_channel
        self.cfg.include_channels[vch] = ChannelState.SAMPLED
        services.preferences_service.update_from_dict({KEY_INCLUDE_CHANNELS: self.cfg.include_channels}, write_disk=False)
        debug(f"[ENGINE] Channel {vch} marked as sampled")

        return True

    def _update_progress(self, rep: int, processed: int, overall_steps: int):
        """
        Update progress after a measurement completes.
        This is the ONLY place step_index is updated (single source of truth).
        """
        progress_pct = round((processed / self.progress.enabled_count) * 100)
        self.progress.percent = progress_pct

        overall_progress_pct = round(((rep * self.progress.enabled_count + processed) / overall_steps) * 100)
        self.progress.overall_percent = overall_progress_pct

        # step_index: total completed measurements (0-based count across all repeats)
        self.progress.step_index = rep * self.progress.enabled_count + processed

        self._refresh_derived_progress()
        debug(
            f"[ENGINE] progress: {progress_pct}% overall_progress: {overall_progress_pct}% "
            f"step_index: {self.progress.step_index}"
        )

    def estimate_total_time_seconds(self) -> float:
        """Estimate total run time for configured measurement (used for frontend ETA display)."""
        if not self.cfg:
            return 0.0

        enabled_indices = [i for i, s in enumerate(self.cfg.include_channels) if s > 0]
        if not enabled_indices:
            return 0.0

        # Total switches: from home to last enabled channel position
        total_switches = enabled_indices[-1]

        total_measure_time = self.progress.enabled_count * float(self.cfg.measure_seconds)
        total_pause_time = self.progress.enabled_count * float(self.cfg.pause_seconds)
        total_switch_time = float(SWITCHING_SETTLE_TIME) + (total_switches * float(SWITCHING_SETTLE_TIME))

        time_per_repeat = total_measure_time + total_pause_time + total_switch_time
        return float(self.cfg.repeat_count) * time_per_repeat + 1.0

    def _finalize_run(self) -> None:
        info("[ENGINE] finalizing MUX measurement task")
