# services.py
from system.gpio.gpio_control import GPIOController
from gasera.tcp_client import GaseraTCPClient
from gasera.controller import GaseraController
from gasera.trigger_monitor import TriggerMonitor
from system.buzzer.buzzer_facade import BuzzerFacade
from gasera.acquisition.base import BaseAcquisitionEngine
from system.motor.motor_control import MotorController
from system.display.display_adapter import DisplayAdapter
from system.display.display_controller import DisplayController

gpio_service: GPIOController = None

motor_controller: MotorController = None

display_controller: DisplayController = None

display_adapter: DisplayAdapter = None

buzzer: BuzzerFacade = None

engine_service: BaseAcquisitionEngine = None

tcp_client: GaseraTCPClient = None

trigger_monitor: TriggerMonitor = None

gasera_controller: GaseraController = None