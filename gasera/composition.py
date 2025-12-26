from gpio.pin_assignments import select_profile
select_profile("optocoupler_board")

DUMMY_VAR = None  # ensure module is initialized

from gasera.acquisition_engine import AcquisitionEngine
from motion.mux_motion import MuxMotion
from mux.mux_gpio import GPIOMux
from mux.mux_vici_uma import ViciUMAMux
from mux.cascaded_mux import CascadedMux
from gpio.pin_assignments import OC1_PIN, OC2_PIN, OC4_PIN, OC5_PIN

# Using persistent symlinks for FTDI devices, at Erciyes University
serial_port1 = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A90KFA3G-if00-port0" # "/dev/ttyUSB0"
serial_port2 = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A9C7BUGI-if00-port0" # "/dev/ttyUSB1"

# GPIO mux
cmux_gpio = CascadedMux(
    GPIOMux(home_pin=OC5_PIN, next_pin=OC4_PIN),
    GPIOMux(home_pin=OC2_PIN, next_pin=OC1_PIN),
)

# Serial mux
cmux_serial = CascadedMux(
    ViciUMAMux(serial_port1),
    ViciUMAMux(serial_port2),
)

motion = MuxMotion(cmux_gpio=cmux_gpio, cmux_serial=cmux_serial)

engine = AcquisitionEngine(motion)
