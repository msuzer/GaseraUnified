# system/display/display_controller.py

import time
from typing import Optional

from system.display.display_state import DisplayState
from system.display_driver import DisplayDriver

class DisplayController:
    def __init__(self, driver: DisplayDriver):
        self.driver = driver
        self.current: Optional[DisplayState] = None
        self.previous: Optional[DisplayState] = None
        self._expire_at: Optional[float] = None
        self._idle = None

    def set_idle_callback(self, idle_callback):
        self._idle = idle_callback

    def show(self, intent: DisplayState):
        if self.current == intent:
            return

        self.previous = self.current
        self.current = intent

        if intent.ttl_seconds:
            self._expire_at = time.time() + intent.ttl_seconds
        else:
            self._expire_at = None

        self._render(intent)

    def tick(self):
        if self._expire_at and time.time() >= self._expire_at:
            self._expire_at = None
            self._auto_return()

    def _auto_return(self):
        if not self.current:
            return
        
        if self.current.return_to == "idle":
            if self._idle:
                self.show(self._idle())
        elif self.current.return_to == "previous" and self.previous:
            self.show(self.previous)

    def _render(self, intent: DisplayState):
        lines = [intent.header] + intent.lines
        while len(lines) < 4:
            lines.append("")
        self.driver.draw_text_lines(lines[:4])

    def update_content(self, state: DisplayState):
        if not self.current:
            return

        updated = DisplayState(
            screen=self.current.screen,
            header=state.header,
            lines=state.lines,
            ttl_seconds=self.current.ttl_seconds,
            return_to=self.current.return_to,
        )

        self.current = updated
        self._render(updated)
