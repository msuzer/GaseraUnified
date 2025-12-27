# system/display_controller.py

import time
from typing import Optional

from system.display.display_state import DisplayState, DisplayMode
from system.display_driver import DisplayDriver


class DisplayController:
    """
    Renders DisplayState snapshots and manages timed screens.
    This class owns:
      - what is currently shown
      - when it expires
      - where to return after expiry

    It does NOT:
      - infer meaning
      - look at engine phases
      - calculate timers
    """

    def __init__(self, driver: DisplayDriver):
        self.driver = driver

        self.current: Optional[DisplayState] = None
        self.previous: Optional[DisplayState] = None

        self._expire_at: Optional[float] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def show(self, state: DisplayState):
        """
        Display a new state immediately.
        """
        if self._same_state(state):
            return

        self.previous = self.current
        self.current = state

        # Setup timed expiry if requested
        if state.ttl_seconds and state.ttl_seconds > 0:
            self._expire_at = time.time() + state.ttl_seconds
        else:
            self._expire_at = None

        self._render(state)

    def tick(self):
        """
        Must be called periodically (e.g. every 200–500 ms).
        Handles timed screen expiry.
        """
        if not self._expire_at:
            return

        if time.time() >= self._expire_at:
            self._expire_at = None
            self._auto_return()

    def clear(self):
        """
        Force clear display and internal state.
        """
        self.current = None
        self.previous = None
        self._expire_at = None
        self.driver.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _auto_return(self):
        """
        Handle automatic return after TTL expiry.
        """
        if not self.current:
            return

        target = self.current.return_to

        if target == "previous" and self.previous:
            self.show(self.previous)
            return

        if target == "idle":
            self.show(self._idle_state())
            return

        # Default: clear screen
        self.clear()

    def _idle_state(self) -> DisplayState:
        return DisplayState(
            mode="idle",
            title="READY",
            subtitle=None,
        )

    def _same_state(self, state: DisplayState) -> bool:
        """
        Prevent unnecessary redraws.
        """
        if not self.current:
            return False

        return (
            self.current.mode == state.mode
            and self.current.title == state.title
            and self.current.subtitle == state.subtitle
            and self.current.et_seconds == state.et_seconds
            and self.current.tt_seconds == state.tt_seconds
            and self.current.step_current == state.step_current
            and self.current.step_total == state.step_total
        )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _render(self, state: DisplayState):
        """
        Render using full-frame adapter.
        """
        # Adapter supports full-state rendering
        if hasattr(self.driver, "draw_full_state"):
            self.driver.draw_full_state(state)
            return

        # Fallback (should not happen)
        self.driver.clear()
