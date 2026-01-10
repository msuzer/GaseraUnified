# services.py
from gasera.acquisition.actions import EngineActions
from gasera.motion.actions import MotionActions
from gasera.motion.iface import MotionInterface
from gasera.sse.device_status_service import DeviceStatusService
from gasera.sse.live_status_service import LiveStatusService
from gasera.sse.motion_status_service import MotionStatusService
from system.gpio.gpio_control import GPIOController
from gasera.controller import GaseraController
from system.buzzer.buzzer_facade import BuzzerFacade
from gasera.acquisition.base import BaseAcquisitionEngine
from system.display.display_adapter import DisplayAdapter
from system.display.display_controller import DisplayController
from system.preferences import Preferences
from system.version_manager import VersionManager

# ------------------------------------------------------------------------------
# Service singletons (initialized in order in device_init.py)
# ------------------------------------------------------------------------------

preferences_service: Preferences = None

gpio_service: GPIOController = None

buzzer_service: BuzzerFacade = None

display_controller: DisplayController = None

display_adapter: DisplayAdapter = None

device_status_service: DeviceStatusService = None

motion_service: MotionInterface = None

engine_service: BaseAcquisitionEngine = None

gasera_controller: GaseraController = None

live_status_service: LiveStatusService = None
 
motion_status_service: MotionStatusService = None
 
version_manager: VersionManager = None

motion_actions: MotionActions = None

engine_actions: EngineActions = None
