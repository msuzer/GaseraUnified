# motor_status_service.py
from __future__ import annotations
from typing import Dict, Any

from system import services


class MotorStatusService:
    """Provides motor status snapshots for SSE consumers."""

    def get_motor_snapshots(self) -> Dict[str, Any] | None:
        motor = getattr(services, "motor_controller", None)
        if motor is None:
            return None

        try:
            return {
                "0": motor.state("0"),
                "1": motor.state("1"),
            }
        except Exception:
            return {"error": True}
