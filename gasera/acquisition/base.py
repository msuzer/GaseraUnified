# gasera/acquisition_engines.py
# Shared base + MUX + Motor engines with a stable Progress contract for the frontend.
#
# Notes:
# - MuxAcquisitionEngine is a refactor of your existing mux AcquisitionEngine (same logic, moved into subclass).  :contentReference[oaicite:0]{index=0}
# - MotorAcquisitionEngine implements user-triggered cycles while preserving the same Progress fields.
# - BaseAcquisitionEngine owns lifecycle/threading/notify/gasera helpers so frontend contract stays consistent.

from __future__ import annotations

import time
import threading

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Callable

from system import services
from gasera.controller import TaskIDs
from gasera.engine_timer import EngineTimer
from gasera.motion.iface import MotionInterface
from gasera.storage_utils import get_log_directory
from system.log_utils import debug, info, warn, error
from gasera.measurement_logger import MeasurementLogger
from gasera.acquisition.task_event import TaskEvent
from gasera.acquisition.phase import Phase
from gasera.acquisition.progress import Progress

from system.preferences import (
    KEY_MEASUREMENT_DURATION,
    KEY_MOTOR_TIMEOUT,
    KEY_PAUSE_SECONDS,
    KEY_REPEAT_COUNT,
)

SWITCHING_SETTLE_TIME = 5.0          # mux settle time
GASERA_CMD_SETTLE_TIME = 1.0         # allow Gasera to process mode/start/stop


@dataclass
class TaskConfig:
    measure_seconds: int
    pause_seconds: int
    motion_timeout: int
    repeat_count: Optional[int] = None  # mux only
    include_channels: Optional[list[int]] = field(default_factory=list)  # mux only
    actuator_ids: Optional[tuple[str, ...]] = None  # motor only

class BaseAcquisitionEngine(ABC):
    def __init__(self, motion: MotionInterface):
        self.motion = motion
        self._worker: Optional[threading.Thread] = None
        self._stop_event = threading.Event()     # abort / error
        self._finish_event = threading.Event()   # graceful end
        self._repeat_event = threading.Event()
        self._lock = threading.RLock()
        self.logger: Optional[MeasurementLogger] = None

        self.cfg: Optional[TaskConfig] = None
        self.progress = Progress()
        self._progress_subs: List[Callable] = []
        self._task_event_subs: List[Callable] = []

        self._last_notified_channel: int = -1
        self._task_timer = EngineTimer()     # measures task active time

    def subscribe_progress_updates(self, cb: Callable[[Progress], None]) -> None:
        self._progress_subs.append(cb)

    def subscribe_task_events(self, cb: Callable[[TaskEvent], None]) -> None:
        self._task_event_subs.append(cb)

    def _get_elapsed_seconds(self) -> float:
        """Return elapsed seconds for progress display."""
        return self._task_timer.elapsed()

    def _emit_progress_updates(self):
        self.progress.elapsed_seconds = self._get_elapsed_seconds()
        from gasera.acquisition.progress_view import ProgressView
        pv = ProgressView(self.progress)
        self.progress.duration_str = pv.duration_label

        for cb in self._progress_subs:
            try:
                cb(self.progress)
            except Exception:
                pass

    def _emit_task_events(self, event: TaskEvent):
        for cb in self._task_event_subs:
            try:
                cb(event)
            except Exception:
                pass

    # -----------------------------
    # Public API
    # -----------------------------
    def start(self) -> tuple[bool, str]:
        with self._lock:
            if self.is_running():
                warn("[ENGINE] start requested but already running")
                services.buzzer.play("busy")
                return False, "Measurement already running"

            self.progress.reset_all() # clear previous state right here before load config
            ok, msg = self._validate_and_load_config()
            if not ok:
                services.buzzer.play("invalid")
                return False, msg

            ok, msg = self._apply_online_mode_preference()
            if not ok:
                services.buzzer.play("error")
                return False, msg

            ok, msg = self._on_start_prepare()
            if not ok:
                services.buzzer.play("error")
                return False, msg

            # Initialize logging
            log_path = get_log_directory()
            self.logger = MeasurementLogger(log_path)

            self._stop_event.clear()
            self._finish_event.clear()
            self._repeat_event.clear()

            self._worker = threading.Thread(target=self._run_loop_wrapper, daemon=True)
            self._worker.start()

            return True, "Measurement Task started"

    def abort(self) -> tuple[bool, str]:
        # Forcefully stop the current task.
        if self.is_running():
            self._stop_event.set()
            self._repeat_event.set()
            self._worker.join(timeout=2.0)
            return True, "Aborted successfully"
        return False, "Not running"

    def finish(self) -> tuple[bool, str]:
        # Gracefully finish the current task.
        if not self._can_finish_now():
            return False, "Finish not allowed in current state"

        self._finish_event.set()
        self._repeat_event.set()
        self._worker.join(timeout=2.0)
        return True, "Finished successfully"

    def trigger_repeat(self) -> tuple[bool, str]:
        # motor will override
        warn("[ENGINE] trigger_repeat not supported by this engine")
        return False, "repeat not supported"

    def is_running(self) -> bool:
        return bool(self._worker) and self._worker.is_alive()

    def _can_finish_now(self) -> bool:
        # motor will override
        info("[ENGINE] not supported by this engine")
        return False

    def _validate_and_load_config(self) -> tuple[bool, str]:
        prefs = services.preferences_service
        cfg = TaskConfig(
            measure_seconds=int(prefs.get(KEY_MEASUREMENT_DURATION, 300)),
            pause_seconds=int(prefs.get(KEY_PAUSE_SECONDS, 300)),
            repeat_count=int(prefs.get(KEY_REPEAT_COUNT, 1)),
            motion_timeout=int(prefs.get(KEY_MOTOR_TIMEOUT, 30))
        )

        self.cfg = cfg
        
        return True, "Configuration valid"

    # -----------------------------
    # Hooks / abstract methods
    # -----------------------------
    @abstractmethod
    def _on_start_prepare(self) -> tuple[bool, str]:
        """Prepare state before starting the measurement run."""
        ...

    @abstractmethod
    def estimate_total_time_seconds(self) -> float:
        """Estimate total time for the entire measurement task."""
        ...

    @abstractmethod
    def _run_loop(self) -> None:
        """Main loop executed in the worker thread."""
        ...

    @abstractmethod
    def _finalize_engine_specifics(self) -> None:
        """Finalize engine-specific summary numbers before the common finalization."""
        ...

    def _finalize_run(self) -> None:
        # 1. Let subclass finalize its summary numbers
        self._task_timer.pause()
        self._finalize_engine_specifics()

        # 2. Final progress formatting
        from gasera.acquisition.progress_view import ProgressView
        pv = ProgressView(self.progress)
        self.progress.progress_str = pv.progress_done_label

        # 3. Resolve final state
        if self._stop_event.is_set():
            self._stop_event.clear()
            self._set_phase(Phase.ABORTED)
            self._emit_task_events(TaskEvent.TASK_ABORTED)
            services.buzzer.play("cancel")
            info("[ENGINE] Measurement run aborted by user")
        else:
            self._set_phase(Phase.IDLE)
            self._emit_task_events(TaskEvent.TASK_FINISHED)
            services.buzzer.play("completed")
            info("[ENGINE] Measurement run complete")

        # 4. Ensure Gasera is stopped
        if not self.check_gasera_idle():
            if not self._stop_measurement():
                warn("[ENGINE] Failed to stop Gasera during finalization")

        # 5. Close logger
        if self.logger:
            self.logger.close()
            self.logger = None

    # -----------------------------
    # Worker wrapper
    # -----------------------------
    def _run_loop_wrapper(self):
        assert self.cfg is not None
        info(
            f"[ENGINE] start: measure={self.cfg.measure_seconds}s, pause={self.cfg.pause_seconds}s, "
            f"repeat={self.cfg.repeat_count}, enabled_channels={self.progress.enabled_count}, motion_timeout={self.cfg.motion_timeout}s"
        )

        try:
            self._task_timer.reset()
            self._run_loop()
        except Exception as e:
            error(f"[ENGINE] unhandled exception: {e}")
            self._stop_event.set()
        finally:
            self._finalize_run()

    # -----------------------------
    # Shared helpers
    # -----------------------------
    def _apply_online_mode_preference(self) -> tuple[bool, str]:
        """Apply SONL/online mode to Gasera (preference is inverted)."""
        try:
            from system.preferences import KEY_ONLINE_MODE_ENABLED
            save_on_gasera = bool(services.preferences_service.get(KEY_ONLINE_MODE_ENABLED, False))
            desired_online_mode = not save_on_gasera  # invert semantics for SONL
            resp_online = services.gasera_controller.set_online_mode(desired_online_mode)
            info(f"[ENGINE] Save On Gasera is {'enabled' if save_on_gasera else 'disabled'} resp={resp_online}")
            time.sleep(GASERA_CMD_SETTLE_TIME)
            return True, "SONL mode applied"
        except Exception as e:
            warn(f"[ENGINE] Failed to apply SONL mode before start: {e}")
            return False, "Failed to apply SONL mode"

    def _start_measurement(self) -> tuple[bool, str]:
        if not self.check_gasera_idle():
            warn("[ENGINE] Gasera not idle")
            return False, "Gasera not idle"

        ok, msg = services.gasera_controller.start_measurement(TaskIDs.DEFAULT)
        if not ok:
            error(f"[ENGINE] Gasera start_measurement failed: {msg}")
            return False, msg

        time.sleep(GASERA_CMD_SETTLE_TIME)
        return True, "Gasera measurement started"

    def _stop_measurement(self) -> bool:
        if self.check_gasera_idle():
            debug("[ENGINE] Gasera already idle")
            return True

        ok, msg = services.gasera_controller.stop_measurement()
        if not ok:
            error(f"[ENGINE] Gasera stop_measurement failed: {msg}")
            return False

        time.sleep(GASERA_CMD_SETTLE_TIME)
        return True

    def check_gasera_stopped(self) -> bool:
        gasera_status = services.device_status_service.get_latest_gasera_status()
        if gasera_status:
            code = gasera_status.get("status_code")
            online = gasera_status.get("online", False)
            if online and code in (1, 2, 4, 7):
                return True
        return False

    def check_gasera_idle(self) -> bool:
        gasera_status = services.device_status_service.get_latest_gasera_status()
        if gasera_status:
            code = gasera_status.get("status_code")
            online = gasera_status.get("online", False)
            if online and code == 2:
                return True
        return False

    def _blocking_wait(self, duration: float, notify: bool = True) -> bool:
        end_time = time.monotonic() + max(0.0, duration)
        base_interval = 0.5 if duration < 10 else 1.0
        while True:
            if self._stop_event.is_set():
                return False

            remaining = end_time - time.monotonic()
            if remaining <= 0:
                break

            if notify:
                self._emit_progress_updates()

            time.sleep(min(base_interval, remaining))
        return True

    def _set_phase(self, phase: str):
        changed = False
        with self._lock:
            if self.progress.phase != phase or self._last_notified_channel != self.progress.current_channel:
                self.progress.phase = phase
                self._last_notified_channel = self.progress.current_channel
                changed = True

        if changed:
            info(f"[ENGINE] phase -> {phase}")
            self._emit_progress_updates()

    # -----------------------------
    # Motion helpers
    # -----------------------------
    def motion_move_and_wait(self, unit_id: Optional[str] = None, was_enabled: bool = True) -> bool:
        self._set_phase(Phase.SWITCHING)

        if was_enabled:
            services.buzzer.play("step")

        self.motion.step(unit_id)
        ok = self._blocking_wait(duration=self.cfg.motion_timeout, notify=True)
        # do not reset here to allow solneoid valve to stay active
        # self.motion.reset(unit_id)

        return ok

    def motion_home_and_wait(self, unit_id: Optional[str] = None) -> bool:
        self._set_phase(Phase.HOMING)

        services.buzzer.play("home")

        self.motion.reset(unit_id) # reset both motor and solenoid valve before homing
        self.motion.home(unit_id)
        ok = self._blocking_wait(duration=self.cfg.motion_timeout, notify=True)
        self.motion.reset(unit_id) # reset in case timeout failure

        return ok

    def on_live_data(self, live_data) -> bool:
        """Shared live data sink (logger dedupe logic lives in MeasurementLogger)."""
        if not live_data or not live_data.get("components"):
            return False

        if self.logger:
            return self.logger.write_measurement(live_data)

        return True
