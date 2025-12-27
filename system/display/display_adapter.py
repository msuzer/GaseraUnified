# system/display_adapter.py

from typing import Optional

from gasera.acquisition.base import Progress
from system.display.display_state import DisplayState, DisplayMode


class DisplayAdapter:
    """
    Converts Progress snapshots into DisplayState.
    ALL semantics live here.
    """

    from gasera.acquisition.base import BaseAcquisitionEngine as AcquisitionEngine
    
    def attach_engine(self, engine: AcquisitionEngine):
        engine.subscribe(self.from_progress)

    def from_progress(
        self,
        p: Progress,
        engine_kind: str,   # "mux" | "motor"
    ) -> DisplayState:
        if engine_kind == "motor":
            return self._motor_state(p)
        else:
            return self._mux_state(p)

    # ------------------------------------------------------------------
    # Motor mapping
    # ------------------------------------------------------------------
    def _motor_state(self, p: Progress) -> DisplayState:
        """
        Motor semantics (locked):
        - elapsed_seconds / tt_seconds → cycle ET/TT while running
        - at end task / abort → summary snapshot already swapped in backend
        """

        # Error / abort → summary screen
        if p.phase == "ABORTED":
            return DisplayState(
                mode="error",
                title="TASK ENDED",
                subtitle="Aborted by user",
                et_seconds=p.elapsed_seconds,
                tt_seconds=p.tt_seconds,
                ttl_seconds=6,
                return_to="idle",
            )

        # Armed (engine started, waiting for trigger)
        if p.phase == "IDLE" and p.tt_seconds:
            return DisplayState(
                mode="armed",
                title="READY",
                subtitle="Awaiting trigger",
                et_seconds=0.0,
                tt_seconds=p.tt_seconds,
            )

        # Running cycle
        if p.phase != "IDLE":
            step_total = p.total_steps or None
            step_current = None
            if step_total:
                # step_index is monotonic; display per-cycle step
                step_current = (p.step_index % step_total) + 1

            return DisplayState(
                mode="running",
                title="MEASURING",
                subtitle=self._motor_subtitle(p),
                et_seconds=p.elapsed_seconds,
                tt_seconds=p.tt_seconds,
                step_current=step_current,
                step_total=step_total,
            )

        # Idle and engine not started yet
        return DisplayState(
            mode="idle",
            title="READY",
            subtitle="Press Start",
        )

    def _motor_subtitle(self, p: Progress) -> Optional[str]:
        if p.enabled_count and p.enabled_count > 1:
            return f"Actuator {p.current_channel + 1} / {p.enabled_count}"
        return "Actuator"

    # ------------------------------------------------------------------
    # MUX mapping
    # ------------------------------------------------------------------
    def _mux_state(self, p: Progress) -> DisplayState:
        """
        MUX semantics:
        - elapsed_seconds / tt_seconds always global
        - IDLE after run = done
        """

        # Error / abort
        if p.phase == "ABORTED":
            return DisplayState(
                mode="error",
                title="MEASUREMENT ABORTED",
                et_seconds=p.elapsed_seconds,
                tt_seconds=p.tt_seconds,
                ttl_seconds=6,
                return_to="idle",
            )

        # Done (IDLE after deterministic run)
        if p.phase == "IDLE" and p.tt_seconds:
            return DisplayState(
                mode="done",
                title="MEASUREMENT DONE",
                subtitle="Completed",
                et_seconds=p.elapsed_seconds,
                tt_seconds=p.tt_seconds,
                ttl_seconds=5,
                return_to="idle",
            )

        # Running
        step_current = p.step_index + 1 if p.total_steps else None

        return DisplayState(
            mode="running",
            title="MEASURING",
            subtitle=self._mux_subtitle(p),
            et_seconds=p.elapsed_seconds,
            tt_seconds=p.tt_seconds,
            step_current=step_current,
            step_total=p.total_steps or None,
        )

    def _mux_subtitle(self, p: Progress) -> Optional[str]:
        if p.enabled_count:
            return f"Ch {p.current_channel + 1} / {p.enabled_count}"
        return None
