# system/display/display_controller.py

import time
from typing import Optional

from system.display.display_state import DisplayState
from system.display_driver import DisplayDriver
from system.display.utils import get_ip_address, get_wifi_ssid, get_gasera_status


class DisplayController:
    def __init__(self, driver: DisplayDriver):
        self.driver = driver
        self.current: Optional[DisplayState] = None
        self.previous: Optional[DisplayState] = None
        self._expire_at: Optional[float] = None

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
            from datetime import datetime
            ip = get_ip_address()
            wifi = get_wifi_ssid()
            gasera = get_gasera_status()
            now = datetime.now().strftime("%d.%m.%Y %H:%M")
            self.show(DisplayState(
                screen="idle",
                header=f"W: {wifi}",
                lines=[f"IP: {ip}", f"G: Gasera {gasera}", f"T: {now}"],
            ))
        elif self.current.return_to == "previous" and self.previous:
            self.show(self.previous)

    def _render(self, intent: DisplayState):
        lines = [intent.header] + intent.lines
        while len(lines) < 4:
            lines.append("")
        self.driver.draw_text_lines(lines[:4])
