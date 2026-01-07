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

    def start(self):
        try:
            info("[ENGINE] Start requested")
            ok, msg = self._engine.start()
            if not ok:
                warn(f"[ENGINE] Start rejected: {msg}")
        except Exception as e:
            warn(f"[ENGINE] Start error: {e}")

    def repeat(self):
        try:
            info("[ENGINE] Repeat requested")
            ok, msg = self._engine.trigger_repeat()
            if not ok:
                warn(f"[ENGINE] Repeat rejected: {msg}")
        except Exception as e:
            warn(f"[ENGINE] Repeat error: {e}")

    def abort(self):
        try:
            info("[ENGINE] Abort requested")
            ok, msg = self._engine.abort()
            if not ok:
                warn(f"[ENGINE] Abort rejected: {msg}")
        except Exception as e:
            warn(f"[ENGINE] Abort error: {e}")

    def finish(self):
        try:
            info("[ENGINE] Finish requested")
            ok, msg = self._engine.finish()
            if not ok:
                warn(f"[ENGINE] Finish rejected: {msg}")
        except Exception as e:
            warn(f"[ENGINE] Finish error: {e}")

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
