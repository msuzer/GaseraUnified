# device/device_profile.py
from enum import Enum

class Device(Enum):
    MUX = "mux"
    MOTOR = "motor"

# CHANGE THIS PER TARGET
DEVICE = Device.MUX
# DEVICE = Device.MOTOR
