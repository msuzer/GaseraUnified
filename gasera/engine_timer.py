import time

class EngineTimer:
    """
    Logical stopwatch.
    - No background thread
    - Explicit start / pause / reset
    - Monotonic time source
    """

    def __init__(self):
        self._running = False
        self._accum = 0.0
        self._last_start = None

    def start(self):
        if not self._running:
            self._last_start = time.monotonic()
            self._running = True

    def pause(self):
        if self._running:
            self._accum += time.monotonic() - self._last_start
            self._last_start = None
            self._running = False

    def reset(self):
        self._running = False
        self._accum = 0.0
        self._last_start = None
        
    def overrite_accumulated(self, seconds: float) -> None:
        self._accum = seconds
        if self._running:
            self._last_start = time.monotonic()

    def elapsed(self) -> float:
        if self._running:
            return self._accum + (time.monotonic() - self._last_start)
        return self._accum
