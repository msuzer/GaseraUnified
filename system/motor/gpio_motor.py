import time
import threading
from system import services

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
        # Re-entrant lock to serialize GPIO access per motor
        self._lock = threading.RLock()
        self._stop_pins()

    @property
    def is_moving(self) -> bool:
        return self._moving

    def _stop_pins(self):
        with self._lock:
            services.gpio_service.reset(self.pin_cw)
            time.sleep(self.settle)
            services.gpio_service.reset(self.pin_ccw)
            time.sleep(self.settle)
            self._moving = False

    def move_forward(self):
        with self._lock:
            services.gpio_service.reset(self.pin_ccw)
            time.sleep(self.settle)
            services.gpio_service.set(self.pin_cw)
            time.sleep(self.settle)
            self._moving = True

    def move_backward(self):
        with self._lock:
            services.gpio_service.reset(self.pin_cw)
            time.sleep(self.settle)
            services.gpio_service.set(self.pin_ccw)
            time.sleep(self.settle)
            self._moving = True

    def stop(self):
        with self._lock:
            # If already stopped, avoid redundant GPIO requests
            if not getattr(self, "_moving", False):
                return
            self._stop_pins()
