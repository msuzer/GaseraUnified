# gasera/motion/actions.py
from gasera.motion.iface import MotionInterface

class MotionActions:
    """
    Canonical motion commands.
    All user-triggered motion MUST go through here.
    """

    def __init__(self, motion: MotionInterface, unit_id=None):
        self._motion = motion
        self._unit_id = unit_id

    def home(self):
        self._motion.home(self._unit_id)

    def step(self):
        self._motion.step(self._unit_id)

    def reset(self):
        self._motion.reset(self._unit_id)
