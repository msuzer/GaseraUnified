# motion/mux_motion.py
from system.mux.cascaded_mux import CascadedMux
from system.mux.mux_gpio import GPIOMux
from system.mux.mux_vici_uma import ViciUMAMux
from system.gpio import pin_assignments as PINS
from system.log_utils import debug

class MuxMotion:
    def __init__(self):
        serial_port1 = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A90KFA3G-if00-port0"
        serial_port2 = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A9C7BUGI-if00-port0"

        self.cmux_gpio = CascadedMux(
            GPIOMux(home_pin=PINS.OC5_PIN, next_pin=PINS.OC4_PIN),
            GPIOMux(home_pin=PINS.OC2_PIN, next_pin=PINS.OC1_PIN),
        )

        self.cmux_serial = CascadedMux(
            ViciUMAMux(serial_port1),
            ViciUMAMux(serial_port2),
        )

        self._pos = 0
        self._state = {"status": "idle", "action": None, "position": self._pos}

    def home(self, unit_id=None):
        self._pos = self.cmux_gpio.home()
        self.cmux_serial.home()
        debug("[MUX] Homing both muxes.")
        self._state = {"status": "moving", "action": "home", "position": self._pos}

    def step(self, unit_id=None):
        self._pos = self.cmux_gpio.select_next()
        self.cmux_serial.select_next()
        debug("[MUX] Stepping both muxes.")
        self._state = {"status": "moving", "action": "step", "position": self._pos}

    def reset(self, unit_id=None):
        self._state = {"status": "idle", "action": "reset", "position": self._pos}
        debug("[MUX] Resetting mux motion state.")
    
    def state(self, unit_id):
        return self._state