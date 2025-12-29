# motor_status_service.py
from __future__ import annotations
from typing import Dict, Any

try:
    from system.services import motor_controller as motor
except Exception:
    motor = None

def get_motor_snapshots() -> Dict[str, Any] | None:
    """
    Return motor status snapshot for SSE.
    - None means: don't include field
    - Dict means: include field
    """
    if motor is None:
        return None

    try:
        return {
            "0": motor.state("0"),
            "1": motor.state("1"),
        }
    except Exception:
        # Fail-soft: don't break SSE
        return {"error": True}
