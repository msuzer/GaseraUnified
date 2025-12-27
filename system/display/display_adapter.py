# system/display_adapter.py

from datetime import datetime

from gasera.acquisition.base import Progress
from system.display.display_state import DisplayState
from system.display.display_controller import DisplayController
from gasera.acquisition.base import BaseAcquisitionEngine as AcquisitionEngine
from gasera.acquisition.mux import MuxAcquisitionEngine
from gasera.acquisition.motor import MotorAcquisitionEngine
from system.display.utils import format_duration, format_consistent_pair, get_ip_address, get_wifi_ssid, get_gasera_status

class DisplayAdapter:
    """
    Converts Progress snapshots into DisplayState.
    ALL semantics live here.
    """
    def __init__(self, controller: DisplayController):
        self._controller = controller
        self._engine = None

    def attach_engine(self, engine: AcquisitionEngine):
        self._engine = engine
        self._engine.subscribe(self.from_progress)

    def from_progress(self, p: Progress) -> DisplayState:
        if isinstance(self._engine, MotorAcquisitionEngine):
            state = self._motor_state(p)
        elif isinstance(self._engine, MuxAcquisitionEngine):
            state = self._mux_state(p)
        else:
            # Defensive fallback
            state = DisplayState(
                screen="error",
                header="DISPLAY ERROR",
                lines=["Unknown engine type"],
                ttl_seconds=5,
                return_to="idle",
            )

        self._controller.show(state)
        return state

    # ------------------------------------------------------------------
    # Motor mapping
    # ------------------------------------------------------------------
    def _motor_state(self, p: Progress) -> DisplayState:
        ip = get_ip_address()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        if p.phase == "ABORTED":
            return DisplayState(
                screen="error",
                header="TASK ENDED",
                lines=[
                    "Aborted by user",
                    f"D: {format_duration(p.elapsed_seconds)}",
                    f"T: {now}",
                ],
                ttl_seconds=10,
                return_to="idle",
            )

        if p.phase == "IDLE" and p.tt_seconds:
            return DisplayState(
                screen="armed",
                header="READY",
                lines=[
                    "Awaiting trigger",
                    f"D: 00:00/{format_duration(p.tt_seconds)}",
                    f"IP: {ip}",
                ],
            )

        if p.phase != "IDLE":
            step = None
            if p.total_steps:
                step = (p.step_index % p.total_steps) + 1

            et_str, tt_str = format_consistent_pair(p.elapsed_seconds, p.tt_seconds)
            lines = [
                f"Ch{p.current_channel + 1} Step {step}/{p.total_steps}",
                f"D: {et_str}/{tt_str}",
                f"IP: {ip}",
            ]

            return DisplayState(
                screen="running",
                header=f"> {p.phase}",
                lines=lines,
            )

        wifi = get_wifi_ssid()
        gasera = get_gasera_status()
        return DisplayState(
            screen="idle",
            header=f"W: {wifi}",
            lines=[f"IP: {ip}", f"G: Gasera {gasera}", f"T: {now}"],
        )

    # ------------------------------------------------------------------
    # Mux mapping
    # ------------------------------------------------------------------
    def _mux_state(self, p: Progress) -> DisplayState:
        ip = get_ip_address()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        et_str, tt_str = format_consistent_pair(p.elapsed_seconds, p.tt_seconds)

        if p.phase == "ABORTED":
            return DisplayState(
                screen="error",
                header="MEASUREMENT ABORTED",
                lines=[
                    f"D: {et_str}/{tt_str}",
                    f"T: {now}",
                ],
                ttl_seconds=10,
                return_to="idle",
            )

        if p.phase == "IDLE" and p.tt_seconds:
            completed_steps = p.step_index if p.step_index else 0
            steps_display = f"{completed_steps}"
            if p.total_steps and p.total_steps > 0:
                steps_display += f"/{p.total_steps}"
            return DisplayState(
                screen="summary",
                header="MEASUREMENT DONE",
                lines=[
                    f"Done: {steps_display} steps",
                    f"D: {et_str}/{tt_str}",
                    f"T: {now}",
                ],
                ttl_seconds=10,
                return_to="idle",
            )

        step = p.step_index + 1 if p.total_steps else None

        lines = [
            f"Ch{p.current_channel + 1} Step {step}/{p.total_steps}",
            f"D: {et_str}/{tt_str}",
            f"IP: {ip}",
        ]

        return DisplayState(
            screen="running",
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
                f"T: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            ],
            ttl_seconds=3,
            return_to="idle",
        )
