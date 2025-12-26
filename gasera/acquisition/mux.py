# gasera/acquisition/mux.py
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from gasera.acquisition.base import BaseAcquisitionEngine, Phase, GASERA_CMD_SETTLE_TIME
from motion.iface import MotionInterface
from gasera.controller import gasera, TaskIDs
from gasera.measurement_logger import MeasurementLogger
from gasera.storage_utils import get_log_directory
from system.log_utils import debug, info, warn, error
from system.preferences import prefs
from buzzer.buzzer_facade import buzzer

from system.preferences import (
    KEY_MEASUREMENT_DURATION,
    KEY_PAUSE_SECONDS,
    KEY_REPEAT_COUNT,
    KEY_INCLUDE_CHANNELS,
    KEY_ONLINE_MODE_ENABLED,
    ChannelState,
)

SWITCHING_SETTLE_TIME = 5.0

@dataclass
class TaskConfig:
    measure_seconds: int
    pause_seconds: int
    repeat_count: int
    include_channels: list[int] = field(default_factory=list)

class MuxAcquisitionEngine(BaseAcquisitionEngine):
    TOTAL_CHANNELS = 31

    def __init__(self, motion: MotionInterface):
        super().__init__()
        self.motion = motion
        self.cfg: Optional[TaskConfig] = None
        self._last_notified_vch: int = -1

    # ---------------- Public API ----------------

    def start(self) -> tuple[bool, str]:
        # keep same signature/behavior as your current MUX engine
        with self._lock:
            if self.is_running():
                warn("[ENGINE] start requested but already running")
                buzzer.play("busy")
                return False, "Measurement already running"

            self._stop_event.clear()

            ok, msg = self._validate_and_load_config()
            if not ok:
                return False, msg

            ok, msg = self._apply_online_mode_preference()
            if not ok:
                return False, msg

            ok, msg = self._start_measurement_mux()
            if not ok:
                buzzer.play("error")
                return False, msg

            self.progress.reset()

            log_path = get_log_directory()
            self.logger = MeasurementLogger(log_path)

            self._start_timestamp = time.time()
            self.progress.tt_seconds = self.estimate_total_time_seconds()
            self.progress.repeat_total = self.cfg.repeat_count
            self.progress.total_steps = self.cfg.repeat_count * self.progress.enabled_count

            import threading
            self._worker = threading.Thread(target=self._run_loop, daemon=True)
            self._worker.start()

            return True, "Measurement Task started"

    def trigger_repeat(self) -> tuple[bool, str]:
        warn("[ENGINE] repeat_trigger not applicable for MUX project")
        return False, "repeat not supported for MUX project"

    # ---------------- Template hooks ----------------

    def _before_repeat(self, rep: int) -> bool:
        return True

    def _repeat_iterator(self):
        return range(self.cfg.repeat_count)

    def _after_repeat(self, rep: int) -> bool:
        return True

    def _run_one_repeat(self, rep: int) -> bool:
        overall_steps = self.progress.enabled_count * self.cfg.repeat_count
        processed = 0

        self.progress.percent = 0
        self.progress.current_channel = 0
        self.progress.next_channel = None
        self._refresh_progress_mux()

        self._home_mux()

        for vch, enabled in enumerate(self.cfg.include_channels):
            self.progress.current_channel = vch
            self.progress.next_channel = (vch + 1) if (vch + 1) < len(self.cfg.include_channels) else None
            self._refresh_progress_mux()

            if self._stop_event.is_set():
                return False

            if enabled > 0:
                if not self._measure_channel():
                    return False
                processed += 1
                self._update_progress_mux(rep, processed, overall_steps)

            is_last_enabled = (processed >= self.progress.enabled_count)
            is_final_repeat = (rep + 1 >= self.cfg.repeat_count)

            if is_last_enabled:
                if is_final_repeat:
                    self._set_phase(Phase.SWITCHING)
                    if not self._blocking_wait(1.0, notify=True):
                        return False
                    debug("[ENGINE] final channel of final repeat - signaled completion")
                break

            if not self._switch_to_next_channel(enabled):
                return False

        self.progress.repeat_index = rep + 1
        return True

    # ---------------- MUX specifics ----------------

    def _validate_and_load_config(self) -> tuple[bool, str]:
        cfg = TaskConfig(
            measure_seconds=int(prefs.get(KEY_MEASUREMENT_DURATION, 100)),
            pause_seconds=int(prefs.get(KEY_PAUSE_SECONDS, 5)),
            repeat_count=int(prefs.get(KEY_REPEAT_COUNT, 1)),
        )
        include_mask = prefs.get(KEY_INCLUDE_CHANNELS, [ChannelState.ACTIVE] * self.TOTAL_CHANNELS)
        cfg.include_channels = list(include_mask)
        self.cfg = cfg

        self.progress.enabled_count = sum(1 for s in self.cfg.include_channels if s > ChannelState.INACTIVE)
        if self.progress.enabled_count == 0:
            warn("[ENGINE] no channels enabled, skipping measurement")
            buzzer.play("invalid")
            return False, "No channels enabled"

        return True, "Configuration valid"

    def _apply_online_mode_preference(self) -> tuple[bool, str]:
        try:
            save_on_gasera = bool(prefs.get(KEY_ONLINE_MODE_ENABLED, False))
            desired_online_mode = not save_on_gasera
            resp_online = gasera.set_online_mode(desired_online_mode)
            info(f"[ENGINE] Applied SONL online_mode={'enabled' if desired_online_mode else 'disabled'} "
                 f"(save_on_gasera={'yes' if save_on_gasera else 'no'}) resp={resp_online}")
            time.sleep(GASERA_CMD_SETTLE_TIME)
            return True, "SONL mode applied"
        except Exception as e:
            warn(f"[ENGINE] Failed to apply SONL mode before start: {e}")
            return False, "Failed to apply SONL mode"

    def _start_measurement_mux(self) -> tuple[bool, str]:
        if not self.check_gasera_idle():
            warn("[ENGINE] Gasera not idle")
            return False, "Gasera not idle"

        ok, msg = gasera.start_measurement(TaskIDs.DEFAULT)
        if not ok:
            error(f"[ENGINE] Gasera start_measurement failed: {msg}")
            return False, msg

        time.sleep(GASERA_CMD_SETTLE_TIME)
        return True, "Gasera measurement started"

    def _home_mux(self):
        self._set_phase(Phase.HOMING)
        buzzer.play("home")
        self.motion.home()
        self._blocking_wait(SWITCHING_SETTLE_TIME, notify=True)

    def _measure_channel(self) -> bool:
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

        vch = self.progress.current_channel
        self.cfg.include_channels[vch] = ChannelState.SAMPLED
        prefs.update_from_dict({KEY_INCLUDE_CHANNELS: self.cfg.include_channels}, write_disk=False)
        debug(f"[ENGINE] Channel {vch} marked as sampled")

        return True

    def _switch_to_next_channel(self, was_enabled: bool) -> bool:
        self._set_phase(Phase.SWITCHING)
        if was_enabled:
            buzzer.play("step")

        self.motion.step()

        if not self._blocking_wait(SWITCHING_SETTLE_TIME, notify=True):
            return False
        return True
    
    def _set_phase(self, phase: str):
        with self._lock:
            if self.progress.phase == phase and self._last_notified_vch == self.progress.current_channel:
                return
            self.progress.phase = phase
            self._last_notified_vch = self.progress.current_channel

        info(f"[ENGINE] phase -> {phase}")
        self._notify()

    def _finalize_run(self):
        if self._stop_event.is_set():
            self._stop_event.clear()
            self._set_phase(Phase.ABORTED)
            buzzer.play("cancel")
        else:
            self._set_phase(Phase.IDLE)
            buzzer.play("completed")
            info("[ENGINE] Measurement run complete")

        # IMPORTANT: stop gasera if still running
        if not self.check_gasera_idle():
            if not self._stop_measurement():
                warn("[ENGINE] Failed to stop Gasera during finalization")

        if self.logger:
            self.logger.close()
            self.logger = None

        self._start_timestamp = None
        self.progress.tt_seconds = None

    def _update_progress_mux(self, rep: int, processed: int, overall_steps: int):
        self.progress.percent = round((processed / self.progress.enabled_count) * 100)
        self.progress.overall_percent = round(((rep * self.progress.enabled_count + processed) / overall_steps) * 100)
        self.progress.step_index = rep * self.progress.enabled_count + processed
        self._refresh_progress_mux()

        debug(f"[ENGINE] progress: {self.progress.percent}% overall: {self.progress.overall_percent}% step_index: {self.progress.step_index}")

    def _refresh_progress_mux(self):
        self.progress.repeat_total = self.cfg.repeat_count if self.cfg else 0
        self.progress.total_steps = (self.progress.repeat_total * self.progress.enabled_count) if self.cfg else 0
        # elapsed is handled by BaseAcquisitionEngine._notify, but we keep this for parity if you want:
        if self._start_timestamp is not None:
            self.progress.elapsed_seconds = max(0.0, time.time() - float(self._start_timestamp))

    def estimate_total_time_seconds(self) -> float:
        if not self.cfg:
            return 0.0

        enabled_indices = [i for i, s in enumerate(self.cfg.include_channels) if s > 0]
        if not enabled_indices:
            return 0.0

        total_switches = enabled_indices[-1]
        total_measure_time = self.progress.enabled_count * float(self.cfg.measure_seconds)
        total_pause_time = self.progress.enabled_count * float(self.cfg.pause_seconds)
        total_switch_time = float(SWITCHING_SETTLE_TIME) + (total_switches * float(SWITCHING_SETTLE_TIME))
        time_per_repeat = total_measure_time + total_pause_time + total_switch_time
        return float(self.cfg.repeat_count) * time_per_repeat + 1.0
