# device/device_init.py
from device.device_profile import DEVICE, Device
from gpio.pin_assignments import select_profile
from system.log_utils import info

def init_device():
    if DEVICE == Device.MUX:
        select_profile("optocoupler_board")
        info("[DEVICE] Initialized MUX hardware profile")

    elif DEVICE == Device.WEBUI:
        select_profile("relay_board")
        info("[DEVICE] Initialized WebUI hardware profile")

    else:
        raise RuntimeError(f"Unsupported device: {DEVICE}")

    from gpio.pin_assignments import BUZZER_PIN
    info(f"[DEVICE] BUZZER_PIN resolved to {BUZZER_PIN}")
