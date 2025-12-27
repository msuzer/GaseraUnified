# system/display_adapter.py

from gasera.acquisition.base import Progress
from system.display.display_state import DisplayState
from system.display.display_controller import DisplayController
from gasera.acquisition.base import BaseAcquisitionEngine as AcquisitionEngine
from gasera.acquisition.mux import MuxAcquisitionEngine
from gasera.acquisition.motor import MotorAcquisitionEngine
from gasera.acquisition.display_event import DisplayEvent
from system.display.utils import format_duration, format_consistent_pair, get_formatted_timestamp, get_ip_address, get_wifi_ssid, get_gasera_status

class DisplayAdapter:
    """
    Converts Progress snapshots into DisplayState.
    ALL semantics live here.
    """
    def __init__(self, controller: DisplayController):
        self._last_progress: Progress | None = None
        self._controller = controller
        self._engine = None

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------
    def attach_engine(self, engine: AcquisitionEngine):
        self._engine = engine
        
        engine.subscribe(self.from_progress)
        
        # DisplayEvent channel is optional → guard it
        if hasattr(engine, "subscribe_display_event"):
            engine.subscribe_display_event(self.from_display_event)

    # ------------------------------------------------------------------
    # Progress = content updates ONLY
    # ------------------------------------------------------------------
    def from_progress(self, p: Progress):
        """
        Progress updates text inside the current screen.
        Must NOT change screen identity.
        """
        self._last_progress = p

        if not self._controller.current:
            return

        if isinstance(self._engine, MotorAcquisitionEngine):
            state = self._motor_content(p)
        elif isinstance(self._engine, MuxAcquisitionEngine):
            state = self._mux_content(p)
        else:
            return
        
        self._controller.update_content(state)

    # ------------------------------------------------------------------
    # DisplayEvent = screen authority
    # ------------------------------------------------------------------
    def from_display_event(self, event: DisplayEvent):
        """
        DisplayEvent is the ONLY authority allowed to change screens.
        """
        if event == DisplayEvent.ENGINE_STARTED:
            self._controller.show(self._idle())

        elif event == DisplayEvent.WAITING_FOR_TRIGGER:
            self._controller.show(self._armed())

        elif event == DisplayEvent.CYCLE_STARTED:
            self._controller.show(self._running())

        elif event == DisplayEvent.TASK_FINISHED:
            self._controller.show(self._summary())

        elif event == DisplayEvent.TASK_ABORTED:
            self._controller.show(self._error("TASK ABORTED"))

        elif event == DisplayEvent.ERROR:
            self._controller.show(self._error("ERROR"))

    # ------------------------------------------------------------------
    # Static screens (no progress dependency)
    # ------------------------------------------------------------------
    def _idle(self) -> DisplayState:
        return DisplayState(
            screen="idle",
            header="READY",
            lines=[get_ip_address()],
        )

    def _armed(self) -> DisplayState:
        return DisplayState(
            screen="armed",
            header="READY",
            lines=["Awaiting trigger", get_ip_address()],
        )

    def _running(self) -> DisplayState:
        return DisplayState(
            screen="running",
            header="MEASURING",
            lines=[],
        )
        
    def _summary(self) -> DisplayState:
        lines = []
        p = self._last_progress
        if p:
            step_str = f"Step {p.step_index}" + (f"/{p.total_steps}" if p.total_steps else "")
            lines.append(step_str)
            et_str, tt_str = format_consistent_pair(p.elapsed_seconds, p.tt_seconds)
            lines.append(f"D: {et_str}/{tt_str}")

        lines.append(f"T: {get_formatted_timestamp()}")

        return DisplayState(
            screen="summary",
            header="MEASUREMENT DONE",
            lines=lines,
            ttl_seconds=10,
            return_to="idle",
        )

    def _error(self, title: str) -> DisplayState:
        lines = []
        p = self._last_progress
        if p:
            step_str = f"Step {p.step_index}" + (f"/{p.total_steps}" if p.total_steps else "")
            lines.append(step_str)
            et_str, tt_str = format_consistent_pair(p.elapsed_seconds, p.tt_seconds)
            lines.append(f"D: {et_str}/{tt_str}")

        lines.append(f"T: {get_formatted_timestamp()}")
        
        return DisplayState(
            screen="error",
            header=title,
            lines=lines,
            ttl_seconds=10,
            return_to="idle",
        )

    # ------------------------------------------------------------------
    # Progress → content (engine-specific)
    # ------------------------------------------------------------------
    def _motor_content(self, p: Progress) -> DisplayState:
        lines = []
        ip = get_ip_address()
        et_str, tt_str = format_consistent_pair(p.elapsed_seconds, p.tt_seconds)
        duration_str = f"D: {et_str}" + (f"/{tt_str}" if (p.tt_seconds and p.tt_seconds > 0) else "")
        step_str = f"Step {p.step_index + 1}" + (f"/{p.total_steps}" if p.total_steps else "")
        header_str = f"> {p.phase}"

        lines.append(f"Ch{p.current_channel + 1} {step_str}")
        lines.append(duration_str)
        lines.append(f"IP: {ip}")

        return DisplayState(
            screen=self._controller.current.screen,
            header=header_str,
            lines=lines,
        )

    def _mux_content(self, p: Progress) -> DisplayState:
        lines = []
        ip = get_ip_address()
        et_str, tt_str = format_consistent_pair(p.elapsed_seconds, p.tt_seconds)
        duration_str = f"D: {et_str}" + (f"/{tt_str}" if (p.tt_seconds and p.tt_seconds > 0) else "")
        step_str = f"Step {p.step_index + 1}" + (f"/{p.total_steps}" if p.total_steps else "")
        header_str = f"> {p.phase}"

        lines.append(f"Ch{p.current_channel + 1} {step_str}")
        lines.append(duration_str)
        lines.append(f"IP: {ip}")

        return DisplayState(
            screen=self._controller.current.screen,
            header=header_str,
            lines=lines,
        )

    def info(self, title: str, subtitle: str) -> DisplayState:
        return DisplayState(
            screen="info",
            header=title,
            lines=[
                subtitle,
                "",
                f"T: {get_formatted_timestamp()}",
            ],
            ttl_seconds=3,
            return_to="idle",
        )
