# composition/webui.py
from gasera.acquisition.motor import MotorAcquisitionEngine as AcquisitionEngine
from motor.bank import MotorBank
from motor.button_monitor import MotorButtonMonitor
from motor.gpio_motor import GPIOMotor
from motor.motor_control import MotorController
from motion.profiles.motor import build_motion
from system import services

from gpio.pin_assignments import (
    MOTOR0_CW_PIN, MOTOR0_CCW_PIN,
    MOTOR1_CW_PIN, MOTOR1_CCW_PIN,
    BOARD_IN1_PIN, BOARD_IN2_PIN,
    BOARD_IN3_PIN, BOARD_IN4_PIN,
)

def build_engine():
    motors = MotorBank({
        "0": GPIOMotor(MOTOR0_CW_PIN, MOTOR0_CCW_PIN),
        "1": GPIOMotor(MOTOR1_CW_PIN, MOTOR1_CCW_PIN),
    })

    services.motor_controller = MotorController(motors)

    button_monitor = MotorButtonMonitor(
        motor_ctrl=services.motor_controller,
        pin_map={
            "M0_CW":  (BOARD_IN1_PIN, ("0", "cw")),
            "M0_CCW": (BOARD_IN2_PIN, ("0", "ccw")),
            "M1_CW":  (BOARD_IN3_PIN, ("1", "cw")),
            "M1_CCW": (BOARD_IN4_PIN, ("1", "ccw")),
        },
        debounce_ms=50,
    )
    button_monitor.start()

    motion = build_motion(motors=motors)

    return AcquisitionEngine(motion)
