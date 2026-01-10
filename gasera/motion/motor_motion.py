# motion/motor_motion.py
from system.log_utils import debug
from system.motor.gpio_motor import GPIOMotor

class MotorMotion:
    def __init__(self, motor_pins: dict[str, tuple[int, int]]):
        """
        motor_pins:
          {
            "0": (cw_pin, ccw_pin),
            "1": (cw_pin, ccw_pin),
          }
        """
        self.motors = {
            mid: GPIOMotor(cw, ccw)
            for mid, (cw, ccw) in motor_pins.items()
        }

        self._state = {
            mid: {"status": "idle", "action": None}
            for mid in self.motors
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
        # Only stop if currently moving to avoid redundant GPIO line requests
        if self.motors[motor_id].is_moving:
            self.motors[motor_id].stop()
            debug(f"[MOTOR] Resetting motor {motor_id}.")
        self._state[motor_id] = {"status": "idle", "action": "reset"}

    def state(self, motor_id):
        return self._state[motor_id]
