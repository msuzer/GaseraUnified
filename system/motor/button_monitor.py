# motor/button_monitor.py
import time
from system import services

class MotorButtonMonitor:
    """
    Edge-based motor button monitor.

    Button semantics:
      - LOW  (pressed)  -> motor.start(motor_id, direction)
      - HIGH (released) -> motor.stop(motor_id)

    This class:
      - does NOT touch motor GPIO pins
      - does NOT manage timeouts
      - does NOT own motor state
    """

    def __init__(self, motor_ctrl, pin_map, debounce_ms=50):
        """
        motor_ctrl : MotorController
        pin_map    : dict[str, tuple[int, tuple[motor_id, direction]]]
                     Example:
                       {
                         "M0_CW":  (PIN_A, ("0", "cw")),
                         "M0_CCW": (PIN_B, ("0", "ccw")),
                         "M1_CW":  (PIN_C, ("1", "cw")),
                         "M1_CCW": (PIN_D, ("1", "ccw")),
                       }
        debounce_ms: debounce window per pin
        """
        self.motor = motor_ctrl
        self.pin_map = pin_map
        self.debounce = debounce_ms / 1000.0
        self._last_edge = {}

    # ------------------------------------------------------------

    def start(self):
        """Register GPIO edge watchers."""
        for _, (pin, action) in self.pin_map.items():
            services.gpio_service.watch(
                pin,
                self._make_handler(pin, action),
                edge="both",
            )

    # ------------------------------------------------------------

    def _make_handler(self, pin, action):
        motor_id, direction = action

        def handler(_, value):
            now = time.monotonic()

            last = self._last_edge.get(pin, 0)
            if now - last < self.debounce:
                return
            self._last_edge[pin] = now

            # LOW = pressed, HIGH = released
            if value == 0:
                self.motor.start(motor_id, direction)
            else:
                self.motor.stop(motor_id)

        return handler
