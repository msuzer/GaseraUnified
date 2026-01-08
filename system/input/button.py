# system/input/button.py
import time
import threading
from system import services

class InputButton:
    """
    Generic active-low button with debounce and release-based
    short/long press detection.

    - Motion logic should use on_press / on_release
    - Short/long press is decided deterministically on release
    """

    def __init__(
        self,
        pin,
        *,
        debounce_ms=200,
        long_press_sec=None,
        on_press=None,
        on_release=None,
        on_short_press=None,
        on_long_press=None,
    ):
        self.pin = pin
        self.debounce = debounce_ms / 1000.0
        self.long_press_sec = long_press_sec

        self.on_press = on_press
        self.on_release = on_release
        self.on_short_press = on_short_press
        self.on_long_press = on_long_press

        self._last_edge = 0.0
        self._stable_level = 1
        self._logical_pressed = False          # debounced logical state
        self._press_start = None       # monotonic timestamp

        self._lock = threading.RLock()

    # --------------------------------------------------

    def start(self):
        services.gpio_service.watch(self.pin, self._on_edge, edge="both")

    # --------------------------------------------------

    def _on_edge(self, _, val):
        # Use monotonic clock to avoid issues if system time changes
        now = time.monotonic()
        val = 1 if int(val) != 0 else 0

        with self._lock:
            # Suppress repeated edges at the same level (bounce),
            # but allow real transitions even within the debounce window
            if now - self._last_edge < self.debounce and val == self._stable_level:
                return

            self._last_edge = now
            # Only act on real transitions
            if val == self._stable_level:
                return

            self._stable_level = val

            if val == 0:
                self._handle_press()
            else:
                self._handle_release()

    # --------------------------------------------------
    # Internal state transitions (debounced)
    # --------------------------------------------------
    def _handle_press(self):
        if not self._logical_pressed:
            self._logical_pressed = True
            self._press_start = time.monotonic()

            if self.on_press:
                self.on_press()

    def _handle_release(self):
        if not self._logical_pressed:
            return

        duration = time.monotonic() - self._press_start

        self._logical_pressed = False
        self._press_start = None

        # Decide gesture first
        if self.long_press_sec is not None and duration >= self.long_press_sec:
            if self.on_long_press:
                self.on_long_press()
        else:
            if self.on_short_press:
                self.on_short_press()

        # Then notify release (e.g. stop motion)
        if self.on_release:
            self.on_release()
