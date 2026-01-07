# motion/motor_motion.py
from system import services


class MotorMotion:
    def home(self, unit_id):
        mc = services.motor_controller
        mc.start(unit_id, "ccw", enable_timeout=True)

    def step(self, unit_id):
        mc = services.motor_controller
        mc.start(unit_id, "cw", enable_timeout=False)
    
    def reset(self, unit_id):
        mc = services.motor_controller
        mc.stop(unit_id)
