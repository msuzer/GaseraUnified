# gasera/acquisition/actions.py
from system.log_utils import info, warn
from gasera.acquisition.motor import MotorAcquisitionEngine
from gasera.acquisition.mux import MuxAcquisitionEngine
from gasera.acquisition.base import BaseAcquisitionEngine


class EngineActions:
    """
    Canonical engine commands.
    All user-triggered engine control MUST go through here.
    """

    def __init__(self, engine: BaseAcquisitionEngine):
        self._engine = engine

    def start(self) -> tuple[bool, str]:
        info("[ENGINE] Start requested")
        ok, msg = self._engine.start()
        if not ok:
            warn(f"[ENGINE] Start rejected: {msg}")
        return ok, msg

    def repeat(self) -> tuple[bool, str]:
        info("[ENGINE] Repeat requested")
        ok, msg = self._engine.trigger_repeat()
        if not ok:
            warn(f"[ENGINE] Repeat rejected: {msg}")
        return ok, msg

    def abort(self) -> tuple[bool, str]:
        warn("[ENGINE] Abort requested")
        ok, msg = self._engine.abort()
        if not ok:
            warn(f"[ENGINE] Abort rejected: {msg}")
        return ok, msg
    
    def finish(self) -> tuple[bool, str]:
        info("[ENGINE] Finish requested")
        ok, msg = self._engine.finish()
        if not ok:
            warn(f"[ENGINE] Finish rejected: {msg}")
        return ok, msg

    def perform_action(self, action: str) -> tuple[bool, str]:
        """
        Perform an action by name.
        """
        action_map = {
            "start": self.start,
            "repeat": self.repeat,
            "abort": self.abort,
            "finish": self.finish,
        }

        if action not in action_map:
            warn(f"[ENGINE] Unknown action requested: {action}")
            return False, "Unknown action"

        return action_map[action]()

    def long_press(self):
        """
        Preserve TriggerMonitor semantics:
        - idle → start
        - running → finish or abort
        """
        if not self._engine.is_running():
            self.start()
            return

        if isinstance(self._engine, MotorAcquisitionEngine):
            if self._engine.can_finish_now():
                self.finish()
            else:
                self.abort()
        elif isinstance(self._engine, MuxAcquisitionEngine):
            self.abort()
        else:
            warn("[ENGINE] Unknown engine type")
