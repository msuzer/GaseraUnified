# motion/motor_motion.py
from system.motor.bank import MotorBank


class MotorMotion:
    def __init__(self, motors: MotorBank):
        self.motors = motors

    def home(self, unit_id):
        self.motors.get(unit_id).move_backward()

    def step(self, unit_id):
        self.motors.get(unit_id).move_forward()
        