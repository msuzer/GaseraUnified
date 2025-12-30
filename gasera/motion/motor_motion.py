# motion/motor_motion.py
from system.motor.bank import MotorBank
from system import services


class MotorMotion:
    def __init__(self, motors: MotorBank):
        self.motors = motors

    def home(self, unit_id):
        mc = services.motor_controller
        
        # prefer motor controller service if available
        if mc is not None:
            mc.start(unit_id, "ccw")
        else:
            self.motors.get(unit_id).move_backward()

    def step(self, unit_id):
        mc = services.motor_controller
        
        # prefer motor controller service if available
        if mc is not None:
            mc.start(unit_id, "cw")
        else:
            self.motors.get(unit_id).move_forward()
    
    def reset(self, unit_id):
        mc = services.motor_controller
        
        # prefer motor controller service if available
        if mc is not None:
            mc.stop(unit_id)
        else:
            self.motors.get(unit_id).stop()
