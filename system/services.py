# services.py
from system.buzzer.buzzer_facade import BuzzerFacade
from gasera.acquisition.base import BaseAcquisitionEngine
from system.motor.motor_control import MotorController
from system.display.display_adapter import DisplayAdapter
from system.display.display_controller import DisplayController

engine_service: BaseAcquisitionEngine = None

motor_controller: MotorController = None

display_controller: DisplayController = None

display_adapter: DisplayAdapter = None

buzzer: BuzzerFacade = None