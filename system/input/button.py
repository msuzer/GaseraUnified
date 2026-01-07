# system/input/button.py
import time
import threading
from system import services

class InputButton:
    """
    Generic active-low button with debounce and optional long press.
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
        self._press_start = None
        self._stable_state = 1
        self._long_timer = None
        self._lock = threading.RLock()

    # --------------------------------------------------

    def start(self):
        services.gpio_service.watch(self.pin, self._on_edge, edge="both")

    # --------------------------------------------------

    def _on_edge(self, _, val):
        now = time.time()
        val = 1 if int(val) != 0 else 0

        with self._lock:
            if now - self._last_edge < self.debounce:
                return

            self._last_edge = now
            self._stable_state = val

            if val == 0:
                self._handle_press()
            else:
                self._handle_release()

    def _handle_press(self):
        self._press_start = time.time()
        if self.on_press:
            self.on_press()

        if self.long_press_sec:
            self._long_timer = threading.Timer(
                self.long_press_sec,
                self._fire_long_if_still_pressed
            )
            self._long_timer.daemon = True
            self._long_timer.start()

    def _handle_release(self):
        now = time.time()

        if self._long_timer and self._long_timer.is_alive():
            self._long_timer.cancel()

        if self._press_start and self.long_press_sec:
            if now - self._press_start < self.long_press_sec:
                if self.on_short_press:
                    self.on_short_press()

        self._press_start = None

        if self.on_release:
            self.on_release()

    def _fire_long_if_still_pressed(self):
        with self._lock:
            if self._stable_state == 0:
                if self.on_long_press:
                    self.on_long_press()
                self._press_start = None
