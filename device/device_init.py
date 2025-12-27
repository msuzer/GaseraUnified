# device/device_init.py
import threading
from device.device_profile import DEVICE, Device
from gpio.pin_assignments import select_profile
from system import services
from system.log_utils import info
from system.display_driver import DisplayDriver
from system.display.lcd_driver_adapter import LCDDriverAdapter
from system.display.display_controller import DisplayController
from system.display.display_adapter import DisplayAdapter

def init_device():
    if DEVICE == Device.MUX:
        select_profile("optocoupler_board")
        info("[DEVICE] Initialized MUX hardware profile")

    elif DEVICE == Device.MOTOR:
        select_profile("relay_board")
        info("[DEVICE] Initialized MOTOR hardware profile")

    else:
        raise RuntimeError(f"Unsupported device: {DEVICE}")

    from gpio.pin_assignments import BUZZER_PIN
    info(f"[DEVICE] BUZZER_PIN resolved to {BUZZER_PIN}")

    driver = DisplayDriver()
    lcd_adapter = LCDDriverAdapter(driver)
    services.display_controller = DisplayController(lcd_adapter)
    services.display_adapter = DisplayAdapter()

def start_display_thread():
    t = threading.Thread(target=services.display_controller.tick, daemon=True, name="display-thread")
    t.start()
