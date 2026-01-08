# motion_status_service.py
from __future__ import annotations
from typing import Dict, Any

from system import services


class MotionStatusService:
    """Provides motion status snapshots for SSE consumers."""

    def get_motion_snapshots(self) -> Dict[str, Any] | None:
        motion = services.motion_service
        if motion is None:
            return None

        snapshots: Dict[str, Any] = {}

        # Collect available units (tolerate missing ones, e.g., mux has only "0")
        for uid in ("0", "1"):
            try:
                st = motion.state(uid)
                if st is not None:
                    snapshots[uid] = st
            except Exception:
                # ignore missing/unsupported units
                pass

        return snapshots if snapshots else {"error": True}
