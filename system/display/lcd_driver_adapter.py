# system/lcd_driver_adapter.py

from typing import Optional, List
from system.display.display_state import DisplayState


class LCDDriverAdapter:
    """
    Adapts DisplayState to DisplayDriver.draw_text_lines().
    No engine logic, no timing logic.
    """

    def __init__(self, driver):
        self._d = driver

    # --- API expected by DisplayController ----------------------------

    def clear(self):
        self._d.clear()

    def draw_title(self, text: str):
        self._render(lines=[text])

    def draw_subtitle(self, text: str):
        self._render(lines=["", text])

    def draw_duration(self, et_seconds: float, tt_seconds: Optional[float]):
        line = self._format_duration(et_seconds, tt_seconds)
        self._render(lines=["", "", line])

    def draw_steps(self, current: int, total: int):
        line = f"Step {current}/{total}"
        self._render(lines=["", "", "", line])

    def draw_footer(self, text: str):
        self._render(lines=["", "", "", text])

    # ------------------------------------------------------------------

    def draw_full_state(self, state: DisplayState):
        """
        Preferred path: render the whole DisplayState at once.
        """
        lines = [""] * 4

        # Line 0: title
        lines[0] = state.title[:20]

        # Line 1: subtitle
        if state.subtitle:
            lines[1] = state.subtitle[:20]

        # Line 2: duration
        if state.et_seconds is not None:
            lines[2] = self._format_duration(
                state.et_seconds, state.tt_seconds
            )

        # Line 3: steps or footer
        if state.step_current and state.step_total:
            lines[3] = f"Step {state.step_current}/{state.step_total}"
        elif state.footer:
            lines[3] = state.footer[:20]

        self._d.draw_text_lines(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _render(self, lines: List[str]):
        padded = [line[:20].ljust(20) for line in lines]
        while len(padded) < 4:
            padded.append(" " * 20)
        self._d.draw_text_lines(padded[:4])

    def _format_duration(self, et: float, tt: Optional[float]) -> str:
        def fmt(sec: float) -> str:
            sec = max(0, int(sec))
            return f"{sec//60:02d}:{sec%60:02d}"

        if tt is not None:
            return f"D: {fmt(et)}/{fmt(tt)}"
        return f"D: {fmt(et)}"
