# ============================================================
# MOTOR ENGINE
# ============================================================
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

from motion.iface import MotionInterface
from system.log_utils import debug, info, warn, error
from system.preferences import prefs
from buzzer.buzzer_facade import buzzer

from gasera.acquisition.base import DEFAULT_ACTUATOR_IDS, SWITCHING_SETTLE_TIME, BaseAcquisitionEngine, Phase

from system.preferences import (
    KEY_MEASUREMENT_DURATION,
    KEY_PAUSE_SECONDS,
    KEY_REPEAT_COUNT,
    KEY_MOTOR_TIMEOUT,
    KEY_INCLUDE_CHANNELS,
    KEY_ONLINE_MODE_ENABLED,
    ChannelState,
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
        self.progress.tt_seconds = None

        return True, "Configuration valid"

    def _on_start_prepare(self) -> tuple[bool, str]:
        self._repeat_event.clear()
        # Best-effort initial homing so first trigger starts cleanly
        try:
            self._home_all_actuators()
        except Exception as e:
            warn(f"[ENGINE] initial homing failed: {e}")
        return True, "ok"

    def _on_stop_unblock(self) -> None:
        # unblock wait()
        self._repeat_event.set()

    def trigger_repeat(self) -> tuple[bool, str]:
        if not self.is_running():
            return False, "Engine is not running"

        with self._lock:
            if self._cycle_in_progress or self._repeat_event.is_set():
                buzzer.play("busy")
                return False, "Cycle already in progress"

            self._repeat_event.set()
            buzzer.play("step")
            return True, "Repeat triggered"

    def _run_loop(self) -> None:
        assert self.cfg is not None
        info(
            f"[ENGINE] start: measure={self.cfg.measure_seconds}s, pause={self.cfg.pause_seconds}s, "
            f"motor_timeout={self.cfg.motor_timeout_sec}s, actuators={self.cfg.actuator_ids}"
        )

        rep = 0
        while not self._stop_event.is_set():
            self._set_phase(Phase.IDLE)

            # wait for trigger
            self._repeat_event.wait()
            if self._stop_event.is_set():
                break

            # consume trigger
            self._repeat_event.clear()

            if not self._run_one_cycle(rep):
                break
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
        self.progress.tt_seconds = None

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
                self._notify()

                if not self._run_actuator_sequence(actuator_id):
                    return False

                # single source of truth for cycle progress
                self._cycle_processed += 1
                self.progress.step_index += 1  # monotonic across whole run
                self._update_cycle_progress(rep, self._cycle_processed)

            self.progress.repeat_index = rep + 1  # completed cycles count
            self._notify()
            buzzer.play("completed")
            return True

        finally:
            if not self._stop_measurement():
                warn("[ENGINE] Failed to stop Gasera after cycle")
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
        self._notify()

    def _home_all_actuators(self):
        assert self.cfg is not None
        self._set_phase(Phase.HOMING)
        buzzer.play("home")

        for idx, actuator_id in enumerate(self.cfg.actuator_ids):
            if self._stop_event.is_set():
                return

            self.progress.current_channel = idx
            self.progress.next_channel = (idx + 1) if (idx + 1 < len(self.cfg.actuator_ids)) else None
            self._notify()

            try:
                self.motion.home(actuator_id)
            except TypeError:
                self.motion.home()

            self._blocking_wait(float(self.cfg.motor_timeout_sec), notify=True)

    def _finalize_run(self) -> None:
        if self._stop_event.is_set():
            self._stop_event.clear()
            self._set_phase(Phase.ABORTED)
            buzzer.play("cancel")
        else:
            self._set_phase(Phase.IDLE)
            buzzer.play("completed")
            info("[ENGINE] Engine run complete")

        # Make sure Gasera is stopped
        if not self.check_gasera_idle():
            if not self._stop_measurement():
                warn("[ENGINE] Failed to stop Gasera during finalization")
