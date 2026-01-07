# device/device_init.py
from system.device.device_profile import DEVICE, Device
from system import services
from system.log_utils import info, debug

def init_device():
    if DEVICE in (Device.MUX, Device.MOTOR):
        from system.gpio.pin_assignments import select_profile
        select_profile(DEVICE)
        info(f"[DEVICE] Initialized {DEVICE.name} hardware profile")
    else:
        raise RuntimeError(f"Unsupported device: {DEVICE}")

    from system.gpio import pin_assignments as PINS
    debug(f"[DEVICE] BUZZER_PIN resolved to {PINS.BUZZER_PIN}")


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

def init_motor_controller():
    from system.motor.motor_control import MotorController
    from system.motor.bank import MotorBank
    from system.motor.gpio_motor import GPIOMotor
    from system.gpio import pin_assignments as PINS

    motors = MotorBank({
        "0": GPIOMotor(PINS.MOTOR0_CW_PIN, PINS.MOTOR0_CCW_PIN),
        "1": GPIOMotor(PINS.MOTOR1_CW_PIN, PINS.MOTOR1_CCW_PIN),
    })

    services.motor_controller = MotorController(motors)

def init_trigger_monitor():
    from gasera.trigger_monitor import TriggerMonitor
    services.trigger_monitor = TriggerMonitor(services.engine_service)
    services.trigger_monitor.start()

def init_button_monitor():
    from system.motor.button_monitor import MotorButtonMonitor
    from system.gpio import pin_assignments as PINS

    button_monitor = MotorButtonMonitor(
        motor_ctrl=services.motor_controller,
        pin_map={
            "M0_CW":  (PINS.BOARD_IN1_PIN, ("0", "cw")),
            "M0_CCW": (PINS.BOARD_IN2_PIN, ("0", "ccw")),
            "M1_CW":  (PINS.BOARD_IN3_PIN, ("1", "cw")),
            "M1_CCW": (PINS.BOARD_IN4_PIN, ("1", "ccw")),
        },
        debounce_ms=200,
    )
    button_monitor.start()
    
def init_engine():
    if DEVICE == Device.MUX:
        from gasera.acquisition.mux import MuxAcquisitionEngine
        from gasera.motion.mux_motion import MuxMotion

        motion = MuxMotion()
        services.engine_service = MuxAcquisitionEngine(motion)
    elif DEVICE == Device.MOTOR:
        from gasera.acquisition.motor import MotorAcquisitionEngine
        from gasera.motion.motor_motion import MotorMotion
        
        init_motor_controller()
        init_button_monitor()
        motion = MotorMotion(services.motor_controller)
        services.engine_service = MotorAcquisitionEngine(motion)
    else:
        raise RuntimeError("Unsupported device")
    

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
