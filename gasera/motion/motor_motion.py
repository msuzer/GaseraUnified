# motion/motor_motion.py
from system.log_utils import debug
from system.motor.gpio_motor import GPIOMotor

class MotorMotion:
    def __init__(self, motors: dict[str, GPIOMotor]):
        self.motors = motors
        self._state = {
            mid: {"status": "idle", "action": None}
            for mid in motors
        }

    def home(self, motor_id):
        self.motors[motor_id].move_backward()
        self._state[motor_id] = {"status": "moving", "action": "home"}
        debug(f"[MOTOR] Homing motor {motor_id}.")

    def step(self, motor_id):
        self.motors[motor_id].move_forward()
        self._state[motor_id] = {"status": "moving", "action": "step"}
        debug(f"[MOTOR] Stepping motor {motor_id}.")

    def reset(self, motor_id):
        self.motors[motor_id].stop()
        debug(f"[MOTOR] Resetting motor {motor_id}.")
        self._state[motor_id] = {"status": "idle", "action": "reset"}

    def state(self, motor_id):
        return self._state[motor_id]
