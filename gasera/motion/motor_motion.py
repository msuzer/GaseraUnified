# motion/motor_motion.py
from system.motor.motor_control import MotorController

class MotorMotion:
    def __init__(self, mc: MotorController=None):
        self.mc = mc
    
    def home(self, unit_id):
        self.mc.start(unit_id, "ccw", enable_timeout=True)

    def step(self, unit_id):
        self.mc.start(unit_id, "cw", enable_timeout=False)
    
    def reset(self, unit_id):
        self.mc.stop(unit_id)
