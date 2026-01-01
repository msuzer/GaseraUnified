# ============================================================
# MOTOR ENGINE
# ============================================================
from __future__ import annotations

from system import services
from gasera.acquisition.task_event import TaskEvent
from gasera.engine_timer import EngineTimer
from gasera.motion.iface import MotionInterface
from system.log_utils import info, warn
from gasera.acquisition.phase import Phase

from gasera.acquisition.base import (
    BaseAcquisitionEngine,
    GASERA_CMD_SETTLE_TIME
)

DEFAULT_ACTUATOR_IDS = ("0", "1")    # motor: logical channels 0/1 for UI

class MotorAcquisitionEngine(BaseAcquisitionEngine):
    """
    User-triggered cycles:
    - trigger_repeat() runs exactly one cycle (left then right), then returns to IDLE
    """

    def __init__(self, motion: MotionInterface):
        super().__init__(motion)

        self._cycle_in_progress = False
        self._task_cumulative_timer = EngineTimer()
        self._armed_waiting_for_repeat = False

    def _validate_and_load_config(self) -> tuple[bool, str]:
        super()._validate_and_load_config()

        self.cfg.actuator_ids=DEFAULT_ACTUATOR_IDS

        # UI contract fields (unbounded run)
        self.progress.enabled_count = len(self.cfg.actuator_ids)
        self.cfg.repeat_count = 0  # unbounded for motor engine

        self.progress.repeat_total = self.cfg.repeat_count # unbounded, increments after each cycle
        self.progress.total_steps = self.progress.enabled_count  # per-cycle, typically 2
        self.progress.tt_seconds = self.estimate_total_time_seconds() # per-cycle estimate

        return True, "Configuration valid"

    def _on_start_prepare(self) -> tuple[bool, str]:
        return True, "ok"

    def _can_finish_now(self) -> bool:
        info("[ENGINE] checking armed state within motor engine")
        return self._armed_waiting_for_repeat

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
        self.progress.repeat_index = 0 # unbounded, increments after each cycle
        self.progress.repeat_total = 0 # repeat_total mirrors repeat_index
        
        self._task_cumulative_timer.reset()
        while not self._stop_event.is_set():
            self._set_phase(Phase.ARMED)
            self._emit_task_event(TaskEvent.WAITING_FOR_TRIGGER)

            self._armed_waiting_for_repeat = True
            self._repeat_event.wait()
            self._repeat_event.clear()
            self._armed_waiting_for_repeat = False

            if self._stop_event.is_set() or self._finish_event.is_set():
                break

            if not self._run_one_cycle():
                break

    def _run_one_cycle(self) -> bool:
        self._cycle_in_progress = True

        # reset cycle UI
        self.progress.percent = 0
        self.progress.overall_percent = 0
        self.progress.step_index = 0  # [0, enabled_count], increments per actuator
        self.progress.elapsed_seconds = 0.0
        
        self._task_timer.reset() # per-cycle timer
        self._task_timer.start() # per-cycle timer
        self._task_cumulative_timer.start() # cumulative timer
        self._emit_task_event(TaskEvent.CYCLE_STARTED)
        
        try:
            ok, msg = self._start_measurement()
            if not ok:
                warn(f"[ENGINE] start_measurement failed: {msg}")
                return False

            for idx, actuator_id in enumerate(self.cfg.actuator_ids):
                if self._stop_event.is_set():
                    return False

                # UI channel mapping
                self.progress.current_channel = idx
                self.progress.next_channel = (idx + 1) if (idx + 1 < len(self.cfg.actuator_ids)) else None
                self._emit_progress_event()

                if not self._run_actuator_sequence(actuator_id):
                    self.motion.reset(actuator_id)
                    return False

                # single source of truth for cycle progress
                self.progress.step_index += 1  # monotonic across cycle
                pct = round((self.progress.step_index / float(self.progress.total_steps)) * 100)
                self.progress.percent = pct
                self.progress.overall_percent = pct # overall percent mirrors cycle percent
                self._emit_progress_event()

            services.buzzer.play("completed")

        finally:
            if not self._stop_measurement():
                warn("[ENGINE] Failed to stop Gasera after cycle completion")

            self._task_timer.pause()
            self._task_cumulative_timer.pause()
            self._cycle_in_progress = False
            self._emit_progress_event()
            
            self.progress.repeat_index += 1
            self.progress.repeat_total += 1 # repeat_total mirrors repeat_index
            self._emit_task_event(TaskEvent.CYCLE_FINISHED)
            info(f"[ENGINE] Cycle complete. Step Index: {self.progress.step_index}, Total Steps: {self.progress.total_steps}")

        return True

    def _run_actuator_sequence(self, actuator_id: str) -> bool:
        """
        One actuator:
          EXTEND -> pause -> measure -> HOME
        """
        assert self.cfg is not None

        # Extend (step, wait, reset) using shared helper
        if not self.motion_move_and_wait(actuator_id):
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

        # Home (home, wait, reset) using shared helper
        if not self.motion_home_and_wait(actuator_id):
            return False

        return True

    def estimate_total_time_seconds(self) -> float:
        per_actuator = (
            float(self.cfg.motion_timeout) +   # extend
            float(self.cfg.pause_seconds) +    # pause
            float(self.cfg.measure_seconds) +  # measure
            float(self.cfg.motion_timeout) +   # home
            float(GASERA_CMD_SETTLE_TIME)      # start/stop instructions settling time 
        )

        return float(self.progress.total_steps) * per_actuator

    def _finalize_run(self) -> None:
        cap = self.progress.repeat_index * float(self.progress.tt_seconds)
        cumulative = self._task_cumulative_timer.elapsed()
        if cumulative > cap:
            cumulative = cap
        self._task_timer.overwrite(cumulative) # show cumulative time on summary screen
        self.progress.tt_seconds = float(cumulative)  # show cumulative time on summary screen

        info("[ENGINE] finalizing motor measurement task")
