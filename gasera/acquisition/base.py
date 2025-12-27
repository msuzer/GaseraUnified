# gasera/acquisition_engines.py
# Shared base + MUX + Motor engines with a stable Progress contract for the frontend.
#
# Notes:
# - MuxAcquisitionEngine is a refactor of your existing mux AcquisitionEngine (same logic, moved into subclass).  :contentReference[oaicite:0]{index=0}
# - MotorAcquisitionEngine implements user-triggered cycles while preserving the same Progress fields.
# - BaseAcquisitionEngine owns lifecycle/threading/notify/gasera helpers so frontend contract stays consistent.

from __future__ import annotations

import threading
import time

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Callable, Iterable

from gasera.device_status_service import get_latest_gasera_status
from motion.iface import MotionInterface

from gasera.storage_utils import get_log_directory
from system.log_utils import debug, info, warn, error
from system.preferences import prefs
from gasera.controller import gasera, TaskIDs
from buzzer.buzzer_facade import buzzer
from gasera.measurement_logger import MeasurementLogger

from system.preferences import (
    KEY_MEASUREMENT_DURATION,
    KEY_PAUSE_SECONDS,
    KEY_REPEAT_COUNT,
    KEY_MOTOR_TIMEOUT,
    KEY_INCLUDE_CHANNELS,
    KEY_ONLINE_MODE_ENABLED,
    ChannelState,
)

# Timing constants
SWITCHING_SETTLE_TIME = 5.0          # mux settle time
GASERA_CMD_SETTLE_TIME = 1.0         # allow Gasera to process mode/start/stop

DEFAULT_ACTUATOR_IDS = ("0", "1")    # motor: logical channels 0/1 for UI


class Phase:
    IDLE = "IDLE"
    HOMING = "HOMING"
    PAUSED = "PAUSED"
    MEASURING = "MEASURING"
    SWITCHING = "SWITCHING"
    ABORTED = "ABORTED"


class Progress:
    """
    Frontend contract (keep stable).
    Snapshot-safe: do NOT add non-serializable fields.
    """

    def __init__(self):
        self.phase = Phase.IDLE
        self.current_channel = 0
        self.next_channel: Optional[int] = None

        # percent: progress within current logical unit (repeat/cycle) 0..100
        self.percent = 0

        # overall_percent: mux -> across all repeats 0..100
        # motor -> typically mirrors percent (unbounded run)
        self.overall_percent = 0

        self.repeat_index = 0
        self.repeat_total: int = 0

        self.enabled_count: int = 0

        # step_index: total completed measurements (monotonic count; mux sets deterministically)
        self.step_index: int = 0

        self.total_steps: int = 0
        self.elapsed_seconds: float = 0.0
        self.tt_seconds: Optional[float] = None

    def reset(self):
        """Reset progress state for a new run."""
        self.phase = Phase.IDLE
        self.current_channel = 0
        self.next_channel = None
        self.percent = 0
        self.overall_percent = 0
        self.repeat_index = 0
        self.step_index = 0
        self.elapsed_seconds = 0.0
        # repeat_total/total_steps/tt_seconds are set by engine on start

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class BaseAcquisitionEngine(ABC):
    """
    Shared engine shell:
    - thread lifecycle
    - stop handling
    - notify/progress refresh
    - gasera helpers
    - logging init/close
    Subclasses implement the run loop semantics and configuration.
    """

    def __init__(self, motion: MotionInterface):
        self.motion = motion
        self._worker: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

        self.progress = Progress()
        self.callbacks: list[Callable[[Progress], None]] = []

        self.logger: Optional[MeasurementLogger] = None

        self._last_notified_vch: int = -1
        self._start_timestamp: Optional[float] = None

    # -----------------------------
    # Public API
    # -----------------------------
    def start(self) -> tuple[bool, str]:
        with self._lock:
            if self.is_running():
                warn("[ENGINE] start requested but already running")
                buzzer.play("busy")
                return False, "Measurement already running"

            self._stop_event.clear()

            ok, msg = self._validate_and_load_config()
            if not ok:
                buzzer.play("invalid")
                return False, msg

            ok, msg = self._apply_online_mode_preference()
            if not ok:
                buzzer.play("error")
                return False, msg

            ok, msg = self._on_start_prepare()
            if not ok:
                buzzer.play("error")
                return False, msg

            # Reset progress for the run
            self.progress.reset()

            # Initialize logging
            log_path = get_log_directory()
            self.logger = MeasurementLogger(log_path)

            self._start_timestamp = time.time()

            self._worker = threading.Thread(target=self._run_loop_wrapper, daemon=True)
            self._worker.start()

            return True, self._start_ok_message()

    def stop(self) -> tuple[bool, str]:
        if self.is_running():
            self._stop_event.set()
            self._on_stop_unblock()
            self._worker.join(timeout=2.0)
            return True, "Stopped successfully"
        return False, "Not running"

    def is_running(self) -> bool:
        return bool(self._worker) and self._worker.is_alive()

    def subscribe(self, cb: Callable[[Progress], None]):
        self.callbacks.append(cb)

    def trigger_repeat(self) -> tuple[bool, str]:
        # Default: not supported unless subclass overrides.
        warn("[ENGINE] trigger_repeat not supported by this engine")
        return False, "repeat not supported"

    # -----------------------------
    # Hooks / abstract methods
    # -----------------------------
    @abstractmethod
    def _validate_and_load_config(self) -> tuple[bool, str]:
        ...

    def _on_start_prepare(self) -> tuple[bool, str]:
        """
        Subclass hook called inside start() after config + SONL applied, before thread starts.
        Default: ok.
        """
        return True, "ok"

    def _start_ok_message(self) -> str:
        return "Engine started"

    def _on_stop_unblock(self) -> None:
        """Subclass may unblock wait primitives (e.g., repeat_event)."""
        return

    @abstractmethod
    def _run_loop(self) -> None:
        """Main loop executed in the worker thread."""
        ...

    @abstractmethod
    def _finalize_run(self) -> None:
        """Finalize state and cleanup (called exactly once)."""
        ...

    # -----------------------------
    # Worker wrapper
    # -----------------------------
    def _run_loop_wrapper(self):
        try:
            self._run_loop()
        finally:
            self._finalize_run()
            # Shared close-out
            if self.logger:
                try:
                    self.logger.close()
                except Exception:
                    pass
                self.logger = None
            # self._start_timestamp = None
            # self.progress.tt_seconds = None

    # -----------------------------
    # Shared helpers
    # -----------------------------
    def _apply_online_mode_preference(self) -> tuple[bool, str]:
        """Apply SONL/online mode to Gasera (preference is inverted)."""
        try:
            save_on_gasera = bool(prefs.get(KEY_ONLINE_MODE_ENABLED, False))
            desired_online_mode = not save_on_gasera  # invert semantics for SONL
            resp_online = gasera.set_online_mode(desired_online_mode)
            info(
                f"[ENGINE] Applied SONL online_mode={'enabled' if desired_online_mode else 'disabled'} "
                f"(save_on_gasera={'yes' if save_on_gasera else 'no'}) resp={resp_online}"
            )
            time.sleep(GASERA_CMD_SETTLE_TIME)
            return True, "SONL mode applied"
        except Exception as e:
            warn(f"[ENGINE] Failed to apply SONL mode before start: {e}")
            return False, "Failed to apply SONL mode"

    def _start_measurement(self) -> tuple[bool, str]:
        if not self.check_gasera_idle():
            warn("[ENGINE] Gasera not idle")
            return False, "Gasera not idle"

        ok, msg = gasera.start_measurement(TaskIDs.DEFAULT)
        if not ok:
            error(f"[ENGINE] Gasera start_measurement failed: {msg}")
            return False, msg

        time.sleep(GASERA_CMD_SETTLE_TIME)
        return True, "Gasera measurement started"

    def _stop_measurement(self) -> bool:
        if self.check_gasera_idle():
            debug("[ENGINE] Gasera already idle")
            return True

        ok, msg = gasera.stop_measurement()
        if not ok:
            error(f"[ENGINE] Gasera stop_measurement failed: {msg}")
            return False

        time.sleep(GASERA_CMD_SETTLE_TIME)
        return True

    def check_gasera_stopped(self) -> bool:
        gasera_status = get_latest_gasera_status()
        if gasera_status:
            code = gasera_status.get("status_code")
            online = gasera_status.get("online", False)
            if online and code in (1, 2, 4, 7):
                return True
        return False

    def check_gasera_idle(self) -> bool:
        gasera_status = get_latest_gasera_status()
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
                self._notify()

            time.sleep(min(base_interval, remaining))
        return True

    def _set_phase(self, phase: str):
        changed = False
        with self._lock:
            if self.progress.phase != phase or self._last_notified_vch != self.progress.current_channel:
                self.progress.phase = phase
                self._last_notified_vch = self.progress.current_channel
                changed = True

        if changed:
            info(f"[ENGINE] phase -> {phase}")
            self._notify()

    def _notify(self):
        self._refresh_derived_progress()
        for cb in self.callbacks:
            try:
                cb(self.progress)
            except Exception as e:
                warn(f"[ENGINE] notify error: {e}")

    def _refresh_derived_progress(self) -> None:
        # elapsed_seconds is always meaningful
        if self._start_timestamp is not None:
            self.progress.elapsed_seconds = max(0.0, time.time() - float(self._start_timestamp))

    def on_live_data(self, live_data) -> bool:
        """Shared live data sink (logger dedupe logic lives in MeasurementLogger)."""
        if not live_data or not live_data.get("components"):
            return False

        if self.logger:
            return self.logger.write_measurement(live_data)

        return True
