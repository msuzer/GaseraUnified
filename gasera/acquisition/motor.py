# gasera/acquisition/motor.py
from __future__ import annotations

import time
import threading
from dataclasses import dataclass
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
    KEY_MOTOR_TIMEOUT,
    KEY_ONLINE_MODE_ENABLED,
)

@dataclass
class TaskConfig:
    measure_seconds: int
    pause_seconds: int
    motor_timeout_sec: int


class MotorAcquisitionEngine(BaseAcquisitionEngine):

    def __init__(self, motion: MotionInterface):
        super().__init__()
        self.motion = motion
        self._repeat_event = threading.Event()
        self.cfg: Optional[TaskConfig] = None

        # MOTOR semantics: always 2 motors
        self.progress.enabled_count = 2

    # ---------------- Public API ----------------

    def start(self) -> tuple[bool, str]:
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

            self.progress.reset()

            self.logger = MeasurementLogger(get_log_directory())
            self._start_timestamp = time.time()

            self._worker = threading.Thread(target=self._run_loop, daemon=True)
            self._worker.start()

            return True, "Measurement Task started"

    def trigger_repeat(self) -> tuple[bool, str]:
        if self._repeat_event.is_set():
            debug("[ENGINE] Repeat already in progress")
            return False, "repeat already in progress"

        self._repeat_event.set()
        return True, "repeat triggered"

    # ---------------- Template hooks ----------------

    def _repeat_iterator(self):
        rep = 0
        self._repeat_event.clear()

        while not self._stop_event.is_set():
            self._repeat_event.wait()
            if self._stop_event.is_set():
                break
            yield rep
            rep += 1

    def _before_repeat(self, rep: int) -> bool:
        ok, msg = self._start_measurement_motor(rep)
        if not ok:
            buzzer.play("error")
            info(f"[ENGINE] Failed to start Gasera measurement before repeat {rep}: {msg}")
            return False
        info(f"[ENGINE] Started Gasera measurement for repeat {rep}")
        return True

    def _run_one_repeat(self, rep: int) -> bool:
        self.progress.repeat_index = rep
        self._notify()

        for motor_id in ("0", "1"):
            self.progress.current_channel = int(motor_id)
            if not self._run_motor_measure_sequence(motor_id):
                return False
            self.progress.step_index += 1
            self._notify()

        self.progress.repeat_index = rep + 1
        return True

    def _after_repeat(self, rep: int) -> bool:
        info(f"[ENGINE] Completed repeat {rep}, stopping Gasera measurement")
        self._repeat_event.clear()
        return self._stop_measurement()

    # ---------------- MOTOR specifics ----------------

    def _validate_and_load_config(self) -> tuple[bool, str]:
        self.cfg = TaskConfig(
            measure_seconds=int(prefs.get(KEY_MEASUREMENT_DURATION, 100)),
            pause_seconds=int(prefs.get(KEY_PAUSE_SECONDS, 5)),
            motor_timeout_sec=int(prefs.get(KEY_MOTOR_TIMEOUT, 10)),
        )
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

    def _start_measurement_motor(self, rep: int) -> tuple[bool, str]:
        if not self.check_gasera_idle():
            warn("[ENGINE] Gasera not idle")
            return False, "Gasera not idle"

        ok, msg = gasera.start_measurement(TaskIDs.DEFAULT)
        if not ok:
            error(f"[ENGINE] Gasera start_measurement failed: {msg}")
            return False, msg

        time.sleep(GASERA_CMD_SETTLE_TIME)
        return True, "Gasera measurement started"

    def _run_motor_measure_sequence(self, motor_id: str) -> bool:
        self._set_phase(Phase.SWITCHING)
        self.motion.step(motor_id)
        if not self._blocking_wait(self.cfg.motor_timeout_sec, notify=True):
            return False

        self._set_phase(Phase.PAUSED)
        if not self._blocking_wait(self.cfg.pause_seconds, notify=True):
            return False

        self._set_phase(Phase.MEASURING)
        if not self._blocking_wait(self.cfg.measure_seconds, notify=True):
            return False

        if self.check_gasera_stopped():
            warn("[ENGINE] Gasera stopped unexpectedly")
            return False

        self._set_phase(Phase.HOMING)
        self.motion.home(motor_id)
        if not self._blocking_wait(self.cfg.motor_timeout_sec, notify=True):
            return False

        return True

    def _finalize_run(self):
        if self._stop_event.is_set():
            self._stop_event.clear()
            self._set_phase(Phase.ABORTED)
            buzzer.play("cancel")
        else:
            self._set_phase(Phase.IDLE)
            buzzer.play("completed")
            info("[ENGINE] Task run complete")

        if not self.check_gasera_idle():
            if not self._stop_measurement():
                warn("[ENGINE] Failed to stop Gasera during finalization")

        if self.logger:
            self.logger.close()
            self.logger = None

        self._start_timestamp = None
