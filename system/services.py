# services.py
from gasera.sse.device_status_service import DeviceStatusService
from gasera.sse.live_status_service import LiveStatusService
from gasera.sse.motor_status_service import MotorStatusService
from system.gpio.gpio_control import GPIOController
from gasera.tcp_client import GaseraTCPClient
from gasera.controller import GaseraController
from gasera.trigger_monitor import TriggerMonitor
from system.buzzer.buzzer_facade import BuzzerFacade
from gasera.acquisition.base import BaseAcquisitionEngine
from system.motor.motor_control import MotorController
from system.display.display_adapter import DisplayAdapter
from system.display.display_controller import DisplayController
from system.preferences import Preferences
from system.version_manager import VersionManager

# ------------------------------------------------------------------------------
# Service singletons (initialized in order in device_init.py)
# ------------------------------------------------------------------------------

gpio_service: GPIOController = None

motor_controller: MotorController = None

display_controller: DisplayController = None

display_adapter: DisplayAdapter = None

buzzer: BuzzerFacade = None

engine_service: BaseAcquisitionEngine = None

tcp_client: GaseraTCPClient = None

trigger_monitor: TriggerMonitor = None

gasera_controller: GaseraController = None

preferences_service: Preferences = None
 
live_status_service: LiveStatusService = None

device_status_service: DeviceStatusService = None
 
motor_status_service: MotorStatusService = None
 
version_manager: VersionManager = None
