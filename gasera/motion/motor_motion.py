# motion/motor_motion.py
from system.log_utils import debug
from system.motor.gpio_motor import GPIOMotor
from system.gpio import pin_assignments as PINS

class MotorMotion:
    def __init__(self):
        self.motors = dict({
            "0": GPIOMotor(PINS.MOTOR0_CW_PIN, PINS.MOTOR0_CCW_PIN),
            "1": GPIOMotor(PINS.MOTOR1_CW_PIN, PINS.MOTOR1_CCW_PIN),
        })
        
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
        self.motors[motor_id].stop()
        debug(f"[MOTOR] Resetting motor {motor_id}.")
        self._state[motor_id] = {"status": "idle", "action": "reset"}

    def state(self, motor_id):
        return self._state[motor_id]
