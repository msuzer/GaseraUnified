# motion/motor_motion.py
class MotorMotion:
    def __init__(self, motors):
        self.motors = motors

    def home(self, unit_id):
        self.motors.get(unit_id).move_backward()

    def step(self, unit_id):
        self.motors.get(unit_id).move_forward()
