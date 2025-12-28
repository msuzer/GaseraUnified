# ============================================================
# MOTOR ENGINE
# ============================================================
from __future__ import annotations

import threading
from dataclasses import dataclass
import time
from typing import Optional

from gasera.acquisition.task_event import TaskEvent
from motion.iface import MotionInterface
from system.log_utils import debug, info, warn, error
from system.preferences import prefs
from system import services

from gasera.acquisition.base import DEFAULT_ACTUATOR_IDS, BaseAcquisitionEngine
from gasera.acquisition.phase import Phase

from system.preferences import (
    KEY_MEASUREMENT_DURATION,
    KEY_PAUSE_SECONDS,
    KEY_MOTOR_TIMEOUT,
)

@dataclass
class MotorTaskConfig:
    measure_seconds: int
    pause_seconds: int
    motor_timeout_sec: int
    actuator_ids: tuple[str, ...] = DEFAULT_ACTUATOR_IDS


class MotorAcquisitionEngine(BaseAcquisitionEngine):
    """
    User-triggered cycles:
    - start() starts thread + homes actuators + goes IDLE
    - trigger_repeat() runs exactly one cycle (left then right), then returns to IDLE
    """

    def __init__(self, motion: MotionInterface):
        super().__init__(motion)
        self.cfg: Optional[MotorTaskConfig] = None

        self._repeat_event = threading.Event()
        self._cycle_in_progress = False
        self._cycle_processed = 0  # completed actuator measurements in current cycle
        self._cycle_start_timestamp: Optional[float] = None
        self._accumulated_seconds: float = 0.0

    def _start_ok_message(self) -> str:
        return "Engine started (waiting for repeat trigger)"

    def _validate_and_load_config(self) -> tuple[bool, str]:
        cfg = MotorTaskConfig(
            measure_seconds=int(prefs.get(KEY_MEASUREMENT_DURATION, 100)),
            pause_seconds=int(prefs.get(KEY_PAUSE_SECONDS, 5)),
            motor_timeout_sec=int(prefs.get(KEY_MOTOR_TIMEOUT, 10)),
            actuator_ids=DEFAULT_ACTUATOR_IDS,
        )
        if cfg.measure_seconds <= 0:
            return False, "Invalid measurement duration"
        if cfg.pause_seconds < 0:
            return False, "Invalid pause duration"
        if cfg.motor_timeout_sec <= 0:
            return False, "Invalid motor timeout"

        self.cfg = cfg

        # UI contract fields (unbounded run)
        self.progress.enabled_count = len(cfg.actuator_ids)
        self.progress.total_steps = self.progress.enabled_count  # per-cycle
        self.progress.repeat_total = 0
        self.progress.tt_seconds = self.estimate_cycle_time_seconds()

        return True, "Configuration valid"

    def _on_start_prepare(self) -> tuple[bool, str]:
        self._repeat_event.clear()
        self._accumulated_seconds = 0.0
        return True, "ok"

    def _on_stop_unblock(self) -> None:
        # unblock wait()
        self._repeat_event.set()

    def trigger_repeat(self) -> tuple[bool, str]:
        if not self.is_running():
            return False, "Engine is not running"

        with self._lock:
            if self._cycle_in_progress or self._repeat_event.is_set():
                services.buzzer.play("busy")
                return False, "Cycle already in progress"

            self._repeat_event.set()
            services.buzzer.play("step")
            return True, "Repeat triggered"

    def _run_loop(self) -> None:
        assert self.cfg is not None
        info(
            f"[ENGINE] start: measure={self.cfg.measure_seconds}s, pause={self.cfg.pause_seconds}s, "
            f"motor_timeout={self.cfg.motor_timeout_sec}s, actuators={self.cfg.actuator_ids}"
        )

        rep = 0
        while not self._stop_event.is_set():
            self._set_phase(Phase.ARMED)
            self._emit_task_event(TaskEvent.WAITING_FOR_TRIGGER)
            
            # wait for trigger
            self._repeat_event.wait()
            if self._stop_event.is_set():
                break

            # consume trigger
            self._repeat_event.clear()

            self._emit_task_event(TaskEvent.CYCLE_STARTED)
            if not self._run_one_cycle(rep):
                break
            
            self._emit_task_event(TaskEvent.CYCLE_FINISHED)
            rep += 1

    def _run_one_cycle(self, rep: int) -> bool:
        assert self.cfg is not None

        self._cycle_in_progress = True
        self._cycle_processed = 0

        # reset cycle UI
        self.progress.percent = 0
        self.progress.overall_percent = 0
        self.progress.total_steps = self.progress.enabled_count  # per-cycle
        self.progress.repeat_total = 0
        self._cycle_start_timestamp = time.time()
        self.progress.elapsed_seconds = 0.0

        ok, msg = self._start_measurement()
        if not ok:
            warn(f"[ENGINE] start_measurement failed: {msg}")
            self._cycle_in_progress = False
            return False

        try:
            for idx, actuator_id in enumerate(self.cfg.actuator_ids):
                if self._stop_event.is_set():
                    return False

                # UI channel mapping
                self.progress.current_channel = idx
                self.progress.next_channel = (idx + 1) if (idx + 1 < len(self.cfg.actuator_ids)) else None
                self._emit_progress_event()

                if not self._run_actuator_sequence(actuator_id):
                    return False

                # single source of truth for cycle progress
                self._cycle_processed += 1
                self.progress.step_index += 1  # monotonic across whole run
                self._update_cycle_progress(rep, self._cycle_processed)

            self.progress.repeat_index = rep + 1  # completed cycles count
            self._emit_progress_event()
            services.buzzer.play("completed")
            return True

        finally:
            if not self._stop_measurement():
                warn("[ENGINE] Failed to stop Gasera after cycle")

            # Accumulate completed (or partial) cycle time
            if self._cycle_start_timestamp is not None:
                self._accumulated_seconds += max(0.0, time.time() - self._cycle_start_timestamp)
            self._cycle_start_timestamp = None
            # Between cycles we show 0/TT (armed)
            self.progress.elapsed_seconds = 0.0

            self._cycle_in_progress = False

    def _run_actuator_sequence(self, actuator_id: str) -> bool:
        """
        One actuator:
          EXTEND -> pause -> measure -> HOME
        """
        assert self.cfg is not None

        # Extend
        self._set_phase(Phase.SWITCHING)
        try:
            self.motion.step(actuator_id)
        except TypeError:
            self.motion.step()
        except Exception as e:
            warn(f"[ENGINE] motion.step({actuator_id}) failed: {e}")
            return False

        if not self._blocking_wait(float(self.cfg.motor_timeout_sec), notify=True):
            return False

        # Pause (settle)
        self._set_phase(Phase.PAUSED)
        if not self._blocking_wait(float(self.cfg.pause_seconds), notify=True):
            return False

        # Measure
        self._set_phase(Phase.MEASURING)
        if not self._blocking_wait(float(self.cfg.measure_seconds), notify=True):
            warn("[ENGINE] measurement interrupted")
            return False

        if self.check_gasera_stopped():
            warn("[ENGINE] Aborting: Gasera stopped unexpectedly")
            return False

        # Home
        self._set_phase(Phase.HOMING)
        try:
            self.motion.home(actuator_id)
        except TypeError:
            self.motion.home()
        except Exception as e:
            warn(f"[ENGINE] motion.home({actuator_id}) failed: {e}")
            return False

        if not self._blocking_wait(float(self.cfg.motor_timeout_sec), notify=True):
            return False

        return True

    def _update_cycle_progress(self, rep: int, processed_in_cycle: int) -> None:
        denom = max(1, self.progress.enabled_count)
        pct = round((processed_in_cycle / denom) * 100)
        self.progress.percent = pct
        # unbounded run: mirror percent (frontend stays happy)
        self.progress.overall_percent = pct

        debug(
            f"[ENGINE] cycle progress: rep={rep} processed={processed_in_cycle}/{denom} "
            f"percent={pct}% step_index={self.progress.step_index}"
        )
        self._emit_progress_event()

    def _home_all_actuators(self):
        assert self.cfg is not None
        self._set_phase(Phase.HOMING)
        services.buzzer.play("home")

        for idx, actuator_id in enumerate(self.cfg.actuator_ids):
            if self._stop_event.is_set():
                return

            self.progress.current_channel = idx
            self.progress.next_channel = (idx + 1) if (idx + 1 < len(self.cfg.actuator_ids)) else None
            self._emit_progress_event()

            try:
                self.motion.home(actuator_id)
            except TypeError:
                self.motion.home()

            self._blocking_wait(float(self.cfg.motor_timeout_sec), notify=True)

    def estimate_cycle_time_seconds(self) -> float:
        if not self.cfg:
            return 0.0

        per_actuator = (
            float(self.cfg.motor_timeout_sec) +   # extend
            float(self.cfg.pause_seconds) +         # pause
            float(self.cfg.measure_seconds) +       # measure
            float(self.cfg.motor_timeout_sec)        # home
        )

        from gasera.acquisition.base import GASERA_CMD_SETTLE_TIME
        return per_actuator * len(self.cfg.actuator_ids) + GASERA_CMD_SETTLE_TIME
    
    def _refresh_derived_progress(self) -> None:
        if self._cycle_start_timestamp is not None:
            self.progress.elapsed_seconds = max(
                0.0, time.time() - self._cycle_start_timestamp
            )
        else:
            # Idle / armed
            self.progress.elapsed_seconds = 0.0

    def _finalize_run(self) -> None:
        if self._cycle_start_timestamp is not None:
            self._accumulated_seconds += max(0.0, time.time() - self._cycle_start_timestamp)
            self._cycle_start_timestamp = None
            self.progress.elapsed_seconds = float(self._accumulated_seconds)
            self.progress.tt_seconds = float(self._accumulated_seconds)
            
        info("[ENGINE] finalizing motor measurement task")