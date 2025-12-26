# gasera/acquisition/base.py
from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from typing import Optional, Callable

from gasera.device_status_service import get_latest_gasera_status
from system.log_utils import debug, info, warn, error
from buzzer.buzzer_facade import buzzer
from gasera.measurement_logger import MeasurementLogger
from gasera.controller import gasera, TaskIDs

GASERA_CMD_SETTLE_TIME = 1.0

class Phase:
    IDLE = "IDLE"
    HOMING = "HOMING"
    PAUSED = "PAUSED"
    MEASURING = "MEASURING"
    SWITCHING = "SWITCHING"
    ABORTED = "ABORTED"

class Progress:
    def __init__(self):
        self.phase = Phase.IDLE
        self.current_channel = 0
        self.next_channel = None
        self.percent = 0
        self.overall_percent = 0
        self.repeat_index = 0
        self.repeat_total = 0
        self.enabled_count = 0
        self.step_index = 0
        self.total_steps = 0
        self.elapsed_seconds = 0.0
        self.tt_seconds = None

    def reset(self):
        self.current_channel = 0
        self.next_channel = None
        self.percent = 0
        self.overall_percent = 0
        self.repeat_index = 0
        self.step_index = 0
        self.elapsed_seconds = 0.0

    def to_dict(self):
        return dict(self.__dict__)


class BaseAcquisitionEngine(ABC):

    def __init__(self):
        self._worker: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self.progress = Progress()
        self.callbacks: list[Callable[[Progress], None]] = []
        self.logger = None
        self._start_timestamp: Optional[float] = None

    # ---------------- Public API ----------------

    def is_running(self) -> bool:
        return bool(self._worker) and self._worker.is_alive()

    def stop(self):
        if self.is_running():
            self._stop_event.set()
            self._worker.join(timeout=2.0)

    def subscribe(self, cb: Callable[[Progress], None]):
        self.callbacks.append(cb)

    # ---------------- Template method ----------------

    def _run_loop(self):
        try:
            for rep in self._repeat_iterator():
                if self._stop_event.is_set():
                    break
                if not self._before_repeat(rep):
                    break
                if not self._run_one_repeat(rep):
                    break
                if not self._after_repeat(rep):
                    break
        finally:
            self._finalize_run()

    @abstractmethod
    def _repeat_iterator(self):
        ...

    @abstractmethod
    def _before_repeat(self, rep: int) -> bool:
        ...

    @abstractmethod
    def _run_one_repeat(self, rep: int) -> bool:
        ...

    @abstractmethod
    def _after_repeat(self, rep: int) -> bool:
        ...
        
    def trigger_repeat(self):
        """
        Optional capability.
        Default: not supported.
        """
        info("[ENGINE] trigger_repeat called but not supported")
        return False, "repeat not supported"

    # ---------------- Shared helpers ----------------

    def _blocking_wait(self, duration: float, notify: bool = True) -> bool:
        end_time = time.monotonic() + duration
        base_interval = 0.5 if duration < 10 else 1.0
        while True:
            if self._stop_event.is_set():
                return False
            now = time.monotonic()
            remaining = end_time - now
            if remaining <= 0:
                break
            if notify:
                self._notify()
            time.sleep(min(base_interval, remaining))
        return True

    def _set_phase(self, phase: str):
        with self._lock:
            if self.progress.phase == phase:
                return
            self.progress.phase = phase
        self._notify()

    def _notify(self):
        if self._start_timestamp is not None:
            self.progress.elapsed_seconds = max(
                0.0, time.time() - float(self._start_timestamp)
            )
        for cb in self.callbacks:
            try:
                cb(self.progress)
            except Exception as e:
                warn(f"[ENGINE] notify error: {e}")

    def on_live_data(self, live_data):
        """Process live data. Returns True if data was new (not duplicate), False otherwise."""
        if not live_data or not live_data.get("components"):
            return False

        if self.logger:
            return self.logger.write_measurement(live_data)
        
        return True

    # ---------------- Gasera helpers ----------------

    def check_gasera_idle(self) -> bool:
        st = get_latest_gasera_status()
        return bool(st and st.get("online") and st.get("status_code") == 2)

    def check_gasera_stopped(self) -> bool:
        st = get_latest_gasera_status()
        return bool(st and st.get("online") and st.get("status_code") in (1, 2, 4, 7))

    def _start_measurement(self) -> bool:
        if not self.check_gasera_idle():
            return False
        ok, _ = gasera.start_measurement(TaskIDs.DEFAULT)
        time.sleep(GASERA_CMD_SETTLE_TIME)
        return ok

    def _stop_measurement(self) -> bool:
        if self.check_gasera_idle():
            return True
        ok, _ = gasera.stop_measurement()
        time.sleep(GASERA_CMD_SETTLE_TIME)
        return ok

    def _finalize_run(self):
        # Generic cleanup only. Specializations decide phase/buzzer/gasera stop policy.
        if self.logger:
            try:
                self.logger.close()
            finally:
                self.logger = None
        self._start_timestamp = None
