# motion/mux_motion.py
from system.mux.cascaded_mux import CascadedMux
from system.mux.mux_gpio import GPIOMux
from system.mux.mux_vici_uma import ViciUMAMux
from system.log_utils import debug

class MuxMotion:
    def __init__(
        self,
        gpio_stages: list[tuple[int, int]],
        serial_ports: list[str] | None = None,
    ):
        """
        gpio_stages:
          [(home_pin, next_pin), (home_pin, next_pin)]

        serial_ports:
          [port1, port2] or None
        """

        gpio_muxes = [
            GPIOMux(home_pin=h, next_pin=n)
            for h, n in gpio_stages
        ]

        self.cmux_gpio = CascadedMux(*gpio_muxes)

        self.cmux_serial = None
        if serial_ports:
            serial_muxes = [ViciUMAMux(p) for p in serial_ports]
            self.cmux_serial = CascadedMux(*serial_muxes)

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