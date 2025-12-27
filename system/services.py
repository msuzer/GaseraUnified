# services.py
from motor.motor_control import MotorController
from system.display.display_adapter import DisplayAdapter
from system.display.display_controller import DisplayController

motor_controller: MotorController = None

display_controller: DisplayController = None

display_adapter: DisplayAdapter = None