# device/device_init.py
from system.device.device_profile import DEVICE, Device
from system.gpio.pin_assignments import select_profile
from system import services
from system.log_utils import info, debug


def init_device():
    if DEVICE == Device.MUX:
        select_profile("optocoupler_board")
        info("[DEVICE] Initialized MUX hardware profile")

    elif DEVICE == Device.MOTOR:
        select_profile("relay_board")
        info("[DEVICE] Initialized MOTOR hardware profile")

    else:
        raise RuntimeError(f"Unsupported device: {DEVICE}")

    from system.gpio import pin_assignments as PINS
    info(f"[DEVICE] BUZZER_PIN resolved to {PINS.BUZZER_PIN}")


def init_gpio_service():
    from system.gpio.gpio_control import GPIOController
    services.gpio_service = GPIOController()
    services.gpio_service.initialize_outputs()


def init_buzzer_service():
    from system.buzzer.buzzer_facade import BuzzerFacade
    import atexit
    
    services.buzzer = BuzzerFacade()
    atexit.register(services.buzzer.shutdown)


def init_preferences_service():
    from system.preferences import Preferences
    services.preferences_service = Preferences()


def init_display_stack():
    from system.display.display_driver import DisplayDriver
    from system.display.display_controller import DisplayController
    from system.display.display_adapter import DisplayAdapter

    driver = DisplayDriver()
    services.display_controller = DisplayController(driver)
    services.display_adapter = DisplayAdapter(services.display_controller)


def init_device_status_service():
    from gasera.sse.device_status_service import DeviceStatusService
    services.device_status_service = DeviceStatusService()
    # register preference callbacks (requires preferences_service to be initialized)
    services.device_status_service.register_callbacks()


def start_device_status_poller():
    # start background poller
    services.device_status_service.start_poller()


def start_display_thread():
    import time, threading
    def run():
        while True:
            services.display_controller.tick()
            time.sleep(0.5)   # 500 ms is perfect

    t = threading.Thread(target=run, daemon=True, name="display-thread")
    t.start()


def init_tcp_client(target_ip: str):
    from gasera.tcp_client import GaseraTCPClient
    services.tcp_client = GaseraTCPClient(target_ip)
    debug(f"[GaseraMux] TCP target: {target_ip}:8888")


def init_gasera_controller():
    from gasera.controller import GaseraController
    services.gasera_controller = GaseraController(services.tcp_client)


def init_trigger_monitor():
    from gasera.trigger_monitor import TriggerMonitor
    services.trigger_monitor = TriggerMonitor(services.engine_service)
    services.trigger_monitor.start()


def init_engine():
    if DEVICE == Device.MUX:
        from gasera.composition.mux import build_engine
    elif DEVICE == Device.MOTOR:
        from gasera.composition.motor import build_engine
    else:
        raise RuntimeError("Unsupported device")

    services.engine_service = build_engine()


def init_live_status_service():
    from gasera.sse.live_status_service import LiveStatusService
    services.live_status_service = LiveStatusService()

    if services.engine_service is not None:
        services.live_status_service.attach_engine(services.engine_service)


def init_live_display_services():
    if services.live_status_service is not None and services.engine_service is not None:
        services.live_status_service.attach_engine(services.engine_service)

    if services.display_adapter is not None and services.engine_service is not None:
        services.display_adapter.attach_engine(services.engine_service)

    if services.live_status_service is not None:
        services.live_status_service.start_background_updater()


def init_motor_status_service():
    from gasera.sse.motor_status_service import MotorStatusService
    services.motor_status_service = MotorStatusService()


def init_version_manager():
    from system.version_manager import VersionManager
    services.version_manager = VersionManager()
