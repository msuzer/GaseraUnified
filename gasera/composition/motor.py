# composition/motor.py
from gasera.acquisition.base import BaseAcquisitionEngine
from gasera.acquisition.motor import MotorAcquisitionEngine as AcquisitionEngine
from gasera.motion.motor_motion import MotorMotion
from system.motor.bank import MotorBank
from system.motor.button_monitor import MotorButtonMonitor
from system.motor.gpio_motor import GPIOMotor
from system.motor.motor_control import MotorController
from system import services
from system.gpio import pin_assignments as PINS

def build_engine() -> BaseAcquisitionEngine:
    motors = MotorBank({
        "0": GPIOMotor(PINS.MOTOR0_CW_PIN, PINS.MOTOR0_CCW_PIN),
        "1": GPIOMotor(PINS.MOTOR1_CW_PIN, PINS.MOTOR1_CCW_PIN),
    })

    services.motor_controller = MotorController(motors)

    button_monitor = MotorButtonMonitor(
        motor_ctrl=services.motor_controller,
        pin_map={
            "M0_CW":  (PINS.BOARD_IN1_PIN, ("0", "cw")),
            "M0_CCW": (PINS.BOARD_IN2_PIN, ("0", "ccw")),
            "M1_CW":  (PINS.BOARD_IN3_PIN, ("1", "cw")),
            "M1_CCW": (PINS.BOARD_IN4_PIN, ("1", "ccw")),
        },
        debounce_ms=50,
    )
    button_monitor.start()

    motion = MotorMotion(motors)

    return AcquisitionEngine(motion)
