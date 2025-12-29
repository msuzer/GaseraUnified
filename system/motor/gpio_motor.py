import time
from system.gpio.gpio_control import gpio


class GPIOMotor:
    """
    Simple GPIO-controlled motor / linear actuator.
    Uses two pins:
      - CW  (forward / extend)
      - CCW (backward / retract)

    Safety:
      - Never allows both pins HIGH at the same time.
    """

    def __init__(self, pin_cw, pin_ccw, *, settle_ms=50):
        self.pin_cw = pin_cw
        self.pin_ccw = pin_ccw
        self.settle = settle_ms / 1000
        self._stop_pins()

    @property
    def is_moving(self) -> bool:
        return self._moving

    def _stop_pins(self):
        gpio.reset(self.pin_cw)
        gpio.reset(self.pin_ccw)
        self._moving = False
        time.sleep(self.settle)

    def move_forward(self):
        self._stop_pins()
        gpio.set(self.pin_cw)
        self._moving = True

    def move_backward(self):
        self._stop_pins()
        gpio.set(self.pin_ccw)
        self._moving = True

    def stop(self):
        self._stop_pins()
