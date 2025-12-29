# composition/mux.py
from gasera.acquisition.base import BaseAcquisitionEngine
from gasera.acquisition.mux import MuxAcquisitionEngine as AcquisitionEngine
from gasera.motion.mux_motion import MuxMotion
from system.mux.mux_gpio import GPIOMux
from system.mux.mux_vici_uma import ViciUMAMux
from system.mux.cascaded_mux import CascadedMux
from system.gpio import pin_assignments as PINS

def build_engine() -> BaseAcquisitionEngine:
    serial_port1 = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A90KFA3G-if00-port0"
    serial_port2 = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A9C7BUGI-if00-port0"

    cmux_gpio = CascadedMux(
        GPIOMux(home_pin=PINS.OC5_PIN, next_pin=PINS.OC4_PIN),
        GPIOMux(home_pin=PINS.OC2_PIN, next_pin=PINS.OC1_PIN),
    )

    cmux_serial = CascadedMux(
        ViciUMAMux(serial_port1),
        ViciUMAMux(serial_port2),
    )

    motion = MuxMotion(cmux_gpio=cmux_gpio, cmux_serial=cmux_serial)

    return AcquisitionEngine(motion)
