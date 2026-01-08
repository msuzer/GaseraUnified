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

def init_motor_buttons():
    from gasera.motion.actions import MotionActions
    from system.input.button import InputButton
    from system.gpio import pin_assignments as PINS

    # Motion binding
    actions_m0: MotionActions = services.motion_actions["0"]
    actions_m1: MotionActions = services.motion_actions["1"]

    buttons = [
        # Motor 0 CW (step)
        InputButton(
            pin=PINS.BOARD_IN1_PIN,
            debounce_ms=200,
            on_press=actions_m0.step,
            on_release=actions_m0.reset,
        ),
        # Motor 0 CCW (home)
        InputButton(
            pin=PINS.BOARD_IN2_PIN,
            debounce_ms=200,
            on_press=actions_m0.home,
            on_release=actions_m0.reset,
        ),
        # Motor 1 CW (step)
        InputButton(
            pin=PINS.BOARD_IN3_PIN,
            debounce_ms=200,
            on_press=actions_m1.step,
            on_release=actions_m1.reset,
        ),
        # Motor 1 CCW (home)
        InputButton(
            pin=PINS.BOARD_IN4_PIN,
            debounce_ms=200,
            on_press=actions_m1.home,
            on_release=actions_m1.reset,
        ),
    ]

    for btn in buttons:
        btn.start()

def init_mux_buttons():
    from gasera.motion.actions import MotionActions
    from system.input.button import InputButton
    from system.gpio import pin_assignments as PINS

    # Motion binding
    actions_m0: MotionActions = services.motion_actions["0"]

    buttons = [
        # Cascaded Mux step
        InputButton(
            pin=PINS.BOARD_IN1_PIN,
            debounce_ms=200,
            on_press=actions_m0.step,
            on_release=actions_m0.reset,
        ),
        # Cascaded Mux home
        InputButton(
            pin=PINS.BOARD_IN2_PIN,
            debounce_ms=200,
            on_press=actions_m0.home,
            on_release=actions_m0.reset,
        ),
    ]

    for btn in buttons:
        btn.start()

def init_trigger():
    from system.input.button import InputButton
    from system.gpio import pin_assignments as PINS
    from system import services

    trigger_btn = InputButton(
        pin=PINS.TRIGGER_PIN,
        debounce_ms=1000,
        long_press_sec=4.0,
        on_short_press=services.engine_actions.repeat,
        on_long_press=services.engine_actions.long_press,
    )

    trigger_btn.start()

def init_engine():
    from gasera.motion.actions import MotionActions
    from gasera.acquisition.actions import EngineActions

    if DEVICE == Device.MUX:
        from gasera.motion.mux_motion import MuxMotion
        motion = MuxMotion()
        services.motion_actions = {
            "0": MotionActions(motion, unit_id="0"),
            # Mux has only one motion unit
        }
        services.motion_service = motion
        from gasera.acquisition.mux import MuxAcquisitionEngine
        services.engine_service = MuxAcquisitionEngine(motion)
        init_mux_buttons()
    elif DEVICE == Device.MOTOR:
        from gasera.motion.motor_motion import MotorMotion
        motion = MotorMotion()
        services.motion_actions = {
            "0": MotionActions(motion, unit_id="0"),
            "1": MotionActions(motion, unit_id="1"),
        }
        services.motion_service = motion
        from gasera.acquisition.motor import MotorAcquisitionEngine
        services.engine_service = MotorAcquisitionEngine(motion)
        init_motor_buttons()
    else:
        raise RuntimeError("Unsupported device")

    services.engine_actions = EngineActions(services.engine_service)
    init_trigger()

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


def init_motion_status_service():
    from gasera.sse.motion_status_service import MotionStatusService
    services.motion_status_service = MotionStatusService()


def init_version_manager():
    from system.version_manager import VersionManager
    services.version_manager = VersionManager()
