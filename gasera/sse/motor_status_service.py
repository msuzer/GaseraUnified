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


# Module-level delegate
def _get_service() -> MotorStatusService | None:
    return getattr(services, "motor_status_service", None)


def get_motor_snapshots() -> Dict[str, Any] | None:
    svc = _get_service()
    if svc is None:
        # fall back to direct lookup to remain tolerant during init
        motor = getattr(services, "motor_controller", None)
        if motor is None:
            return None
        try:
            return {"0": motor.state("0"), "1": motor.state("1")}
        except Exception:
            return {"error": True}

    return svc.get_motor_snapshots()
