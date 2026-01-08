# motion_status_service.py
from __future__ import annotations
from typing import Dict, Any

from system import services


class MotionStatusService:
    """Provides motion status snapshots for SSE consumers."""

    def get_motion_snapshots(self) -> Dict[str, Any] | None:
        motion = services.motion_service
        actions = services.motion_actions
        if motion is None or not actions:
            return None

        snapshots: Dict[str, Any] = {}

        for uid in actions.keys():
            try:
                st = motion.state(uid)
                if st is not None:
                    snapshots[uid] = st
            except Exception:
                pass

        return snapshots if snapshots else {"error": True}
