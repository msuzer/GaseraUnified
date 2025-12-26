# composition/__init__.py
from device.device_profile import DEVICE, Device

if DEVICE == Device.MUX:
    from composition.mux import build_engine
elif DEVICE == Device.WEBUI:
    from composition.webui import build_engine
else:
    raise RuntimeError("Unsupported device")

engine = build_engine()
