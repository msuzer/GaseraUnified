# gasera/motion/actions.py
from gasera.motion.iface import MotionInterface
from system import services
from system.log_utils import debug

class MotionActions:
    """
    Canonical motion commands.
    All user-triggered motion MUST go through here.
    """

    def __init__(self, motion: MotionInterface, unit_id=None):
        self._motion = motion
        self._unit_id = unit_id

    def _allowed(self) -> bool:
        if services.engine_service is None:
            return True
        return not services.engine_service.is_in_active_phase()

    def home(self):
        if not self._allowed():
            debug("[MOTION] Ignored home action while engine running")
            return

        self._motion.home(self._unit_id)

    def step(self):
        if not self._allowed():
            debug("[MOTION] Ignored step action while engine running")
            return

        self._motion.step(self._unit_id)

    def reset(self):
        if not self._allowed():
            debug("[MOTION] Ignored reset action while engine running")
            return

        self._motion.reset(self._unit_id)
