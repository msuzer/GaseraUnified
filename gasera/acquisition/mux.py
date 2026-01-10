# ============================================================
# MUX ENGINE
# ============================================================
from __future__ import annotations

from system import services
from system.log_utils import debug, info, warn
from gasera.acquisition.task_event import TaskEvent
from gasera.motion.iface import MotionInterface
from gasera.acquisition.phase import Phase
from gasera.acquisition.progress_view import ProgressView

from gasera.acquisition.base import (
    BaseAcquisitionEngine,
    GASERA_CMD_SETTLE_TIME,
    SWITCHING_SETTLE_TIME
)

from system.preferences import (
    ChannelState,
    KEY_INCLUDE_CHANNELS
)

class MuxAcquisitionEngine(BaseAcquisitionEngine):
    """
    Deterministic (configured channels + repeat_count).
    Refactor of your mux AcquisitionEngine into BaseAcquisitionEngine subclass.  :contentReference[oaicite:1]{index=1}
    """

    TOTAL_CHANNELS = 31

    def __init__(self, motion: MotionInterface):
        super().__init__(motion)

    def _validate_and_load_config(self) -> tuple[bool, str]:
        super()._validate_and_load_config()

        prefs = services.preferences_service

        include_mask = prefs.get(KEY_INCLUDE_CHANNELS, [ChannelState.ACTIVE] * self.TOTAL_CHANNELS)
        self.cfg.include_channels = list(include_mask)

        self.progress.enabled_count = sum(1 for s in self.cfg.include_channels if s > ChannelState.INACTIVE)
        if self.progress.enabled_count == 0:
            warn("[ENGINE] no channels enabled, skipping measurement")
            services.buzzer_service.play("invalid")
            return False, "No channels enabled"

        self.cfg.motion_timeout = SWITCHING_SETTLE_TIME # const for mux switching
        
        self.progress.repeat_total = self.cfg.repeat_count
        self.progress.total_steps = self.cfg.repeat_count * self.progress.enabled_count
        self.progress.tt_seconds = self.estimate_total_time_seconds()

        return True, "Configuration valid"

    def _on_start_prepare(self) -> tuple[bool, str]:
        assert self.cfg is not None

        info("[ENGINE] Starting Gasera measurement")
        ok, msg = self._start_measurement()
        if not ok:
            return False, msg

        self._emit_task_events(TaskEvent.TASK_STARTED)

        return True, "ok"

    def _run_loop(self) -> None:
        self._task_timer.start() # mux starts timer at beginning of entire task
        for rep in range(self.cfg.repeat_count):
            if self._stop_event.is_set():
                break
            if not self._run_one_repeat(rep):
                break

    def _run_one_repeat(self, rep: int) -> bool:
        
        # reset repeat UI
        self.progress.step_index = 0
        self.progress.percent = 0
        self.progress.current_channel = 0
        self.progress.next_channel = None
        self.motion_home_and_wait()
        
        for channel, enabled in enumerate(self.cfg.include_channels):
            self.progress.current_channel = channel
            next_channel = channel + 1
            self.progress.next_channel = next_channel if next_channel < len(self.cfg.include_channels) else None

            if self._stop_event.is_set():
                return False

            if enabled > 0:
                if not self._measure_channel():
                    return False

                self.progress.step_index += 1
                self._update_progress()

            is_last_enabled = (self.progress.step_index >= self.progress.enabled_count)
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
        self._set_phase(Phase.PAUSED)
        if not self._blocking_wait(self.cfg.pause_seconds, notify=True):
            warn("[ENGINE] Aborting: measurement interrupted")
            return False

        self._set_phase(Phase.MEASURING)
        if not self._blocking_wait(self.cfg.measure_seconds, notify=True):
            warn("[ENGINE] Aborting: measurement interrupted")
            return False

        if self.check_gasera_stopped():
            warn("[ENGINE] Aborting: Gasera stopped unexpectedly")
            return False

        # Mark channel as sampled (memory only, no disk write)
        channel = self.progress.current_channel
        self.cfg.include_channels[channel] = ChannelState.SAMPLED
        services.preferences_service.update_from_dict({KEY_INCLUDE_CHANNELS: self.cfg.include_channels}, write_disk=False)
        debug(f"[ENGINE] Channel {channel} marked as sampled")

        return True

    def _update_progress(self):
        """
        Update progress after a measurement completes.
        This is the ONLY place step_index is updated (single source of truth).
        """
        progress_pct = round((self.progress.step_index / self.progress.enabled_count) * 100)
        self.progress.percent = progress_pct

        overall_progress_pct = round(((self.progress.repeat_index * self.progress.enabled_count + self.progress.step_index) / self.progress.total_steps) * 100)
        self.progress.overall_percent = overall_progress_pct

        # step_index: total completed measurements (0-based count across all repeats)
        # self.progress.step_index = repeat_index * self.progress.enabled_count + steps_completed_in_single_repeat
        self.progress.step_index = self.progress.step_index
        
        debug(
            f"[ENGINE] progress: {progress_pct}% overall_progress: {overall_progress_pct}% "
            f"step_index: {self.progress.step_index}"
        )

    def estimate_total_time_seconds(self) -> float:
        per_channel = (
            float(self.cfg.pause_seconds) + 
            float(self.cfg.measure_seconds) +
            float(self.cfg.motion_timeout)
        )
        
        return float(self.progress.total_steps) * per_channel + float(GASERA_CMD_SETTLE_TIME)

    def _finalize_engine_specifics(self, pv: ProgressView) -> None:
        self.progress.progress_str = pv.mux_step_label

        info("[ENGINE] finalizing MUX measurement task")
