# device/device_init.py
from system.device.device_profile import DEVICE, Device
from system.gpio.pin_assignments import select_profile
from system import services
from system.log_utils import info

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

    # Initialize outputs after profile selection
    from system.gpio.gpio_control import initialize_outputs
    initialize_outputs()

def init_engine():
    if DEVICE == Device.MUX:
        from gasera.composition.mux import build_engine
    elif DEVICE == Device.MOTOR:
        from gasera.composition.motor import build_engine
    else:
        raise RuntimeError("Unsupported device")

    services.engine_service = build_engine()

def init_buzzer_service():
    from system.buzzer.buzzer_facade import BuzzerFacade
    import atexit
    
    services.buzzer = BuzzerFacade()
    atexit.register(services.buzzer.shutdown)

def init_display_stack():
    from system.display.display_driver import DisplayDriver
    from system.display.display_controller import DisplayController
    from system.display.display_adapter import DisplayAdapter

    driver = DisplayDriver()
    services.display_controller = DisplayController(driver)
    services.display_adapter = DisplayAdapter(services.display_controller)

def start_display_thread():
    import time, threading
    def run():
        while True:
            services.display_controller.tick()
            time.sleep(0.5)   # 500 ms is perfect

    t = threading.Thread(target=run, daemon=True, name="display-thread")
    t.start()
