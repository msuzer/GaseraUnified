# system/display_adapter.py

from gasera.acquisition.base import Progress
from system.display.display_state import DisplayState
from system.display.display_controller import DisplayController
from gasera.acquisition.base import BaseAcquisitionEngine as AcquisitionEngine
from gasera.acquisition.mux import MuxAcquisitionEngine
from gasera.acquisition.motor import MotorAcquisitionEngine
from gasera.acquisition.task_event import TaskEvent
from system.utils import get_formatted_timestamp, get_ip_address, get_wifi_ssid, get_gasera_status
from gasera.acquisition.progress_view import ProgressView

class DisplayAdapter:
    """
    Converts Progress snapshots into DisplayState.
    ALL semantics live here.
    """
    def __init__(self, controller: DisplayController):
        self._last_progress: Progress | None = None
        self._controller = controller
        self._controller.set_idle_callback(self._idle)
        self._controller.set_refresh_callback(self._refresh, interval_seconds=10.0)
        self._engine = None

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------
    def attach_engine(self, engine: AcquisitionEngine) -> None:
        self._engine = engine
        
        engine.subscribe(self.from_progress)
        
        # TaskEvent channel is optional → guard it
        if hasattr(engine, "subscribe_task_event"):
            engine.subscribe_task_event(self.from_task_event)

    def _refresh(self):
        """
        Periodic content refresh (time/IP/etc).
        Does NOT change screen.
        """
        if not self._controller.current:
            return

        screen = self._controller.current.screen

        if screen == "idle":
            self._controller.update_content(self._idle())
        elif screen == "armed":
            self._controller.update_content(self._armed())

    # ------------------------------------------------------------------
    # Progress = content updates ONLY
    # ------------------------------------------------------------------
    def from_progress(self, p: Progress) -> None:
        """
        Progress updates text inside the current screen.
        Must NOT change screen identity.
        """
        self._last_progress = p

        if not self._controller.current:
            return

        if isinstance(self._engine, MotorAcquisitionEngine):
            if self._controller.current.screen != "running":
                return

        if isinstance(self._engine, MotorAcquisitionEngine):
            state = self._motor_content(p)
        elif isinstance(self._engine, MuxAcquisitionEngine):
            state = self._mux_content(p)
        else:
            return
        
        self._controller.update_content(state)

    # ------------------------------------------------------------------
    # TaskEvent = screen authority
    # ------------------------------------------------------------------
    def from_task_event(self, event: TaskEvent) -> None:
        """
        DisplayEvent is the ONLY authority allowed to change screens.
        """
        if event == TaskEvent.TASK_STARTED:
            self._controller.show(self._running())

        elif event == TaskEvent.WAITING_FOR_TRIGGER:
            self._controller.show(self._armed())

        elif event == TaskEvent.CYCLE_STARTED:
            self._controller.show(self._running())

        elif event == TaskEvent.TASK_FINISHED:
            self._controller.show(self._summary())

        elif event == TaskEvent.TASK_ABORTED:
            self._controller.show(self._error("TASK ABORTED"))

        elif event == TaskEvent.ERROR:
            self._controller.show(self._error("ERROR"))

    # ------------------------------------------------------------------
    # Static screens (no progress dependency)
    # ------------------------------------------------------------------
    def _idle(self) -> DisplayState:
        lines = []
        lines.append(f"IP: {get_ip_address()}")
        lines.append(f"G: Gasera {get_gasera_status()}")
        lines.append(f"T: {get_formatted_timestamp()}")

        return DisplayState(
            screen="idle",
            header=f"W: {get_wifi_ssid()}",
            lines=lines,
        )

    def _armed(self) -> DisplayState:
        lines = [""]
        lines.append(f"T: {get_formatted_timestamp()}")
        lines.append(f"IP: {get_ip_address()}")

        return DisplayState(
            screen="armed",
            header="Awaiting trigger",
            lines=lines,
        )

    def _running(self) -> DisplayState:
        return DisplayState(
            screen="running",
            header="MEASURING",
            lines=[],
        )
        
    def _summary(self) -> DisplayState:
        lines = []
        if self._last_progress:
            pv = ProgressView(self._last_progress)
            if pv:
                if pv.channel_step_label:
                    lines.append(pv.channel_step_label)
                if pv.duration_label:
                    lines.append(pv.duration_label)

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
        if self._last_progress:
            pv = ProgressView(self._last_progress)
            if pv:
                if pv.channel_step_label:
                    lines.append(pv.channel_step_label)
                if pv.duration_label:
                    lines.append(pv.duration_label)

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
        pv = ProgressView(p)
        lines = []
        if pv:
            if pv.channel_step_label:
                lines.append(pv.channel_step_label)
            if pv.duration_label:
                lines.append(pv.duration_label)
        
        lines.append(f"IP: {get_ip_address()}")

        return DisplayState(
            screen=self._controller.current.screen,
            header=f"> {p.phase}",
            lines=lines,
        )

    def _mux_content(self, p: Progress) -> DisplayState:
        pv = ProgressView(p)
        lines = []
        if pv:
            if pv.channel_step_label:
                lines.append(pv.channel_step_label)
            if pv.duration_label:
                lines.append(pv.duration_label)
        
        lines.append(f"IP: {get_ip_address()}")

        return DisplayState(
            screen=self._controller.current.screen,
            header=f"> {p.phase}",
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
