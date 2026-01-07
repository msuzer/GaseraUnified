# motor_status_service.py
from __future__ import annotations
from typing import Dict, Any

from system import services


class MotorStatusService:
    """Provides motor status snapshots for SSE consumers."""

    def get_motor_snapshots(self) -> Dict[str, Any] | None:
        motion = services.motion_service
        if motion is None:
            return None

        try:
            return {
                "0": motion.state("0"),
                "1": motion.state("1"),
            }
        except Exception:
            return {"error": True}
