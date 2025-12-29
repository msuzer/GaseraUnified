# live_status_service.py
from __future__ import annotations
import threading
import time
from datetime import datetime
from typing import Dict, Any, Tuple

from system.log_utils import warn, error
from gasera.controller import gasera
from gasera.acquisition.mux import MuxAcquisitionEngine as AcquisitionEngine
from gasera.acquisition.base import Progress, Phase

# High-frequency data snapshots (progress + live measurements)
latest_progress_snapshot: Dict[str, Any] = {"phase": Phase.IDLE, "current_channel": 0, "repeat_index": 0}
latest_live_data: Dict[str, Any] = {}

_lock = threading.Lock()  # Protect access to latest_* globals
SSE_UPDATE_INTERVAL = 25.0
_updater_stop_event = threading.Event()
_engine: AcquisitionEngine | None = None


def init(engine: AcquisitionEngine) -> None:
    global _engine
    _engine = engine
    engine.subscribe(_on_progress)

def _on_progress(progress: Progress) -> None:
    global latest_progress_snapshot
    try:
        snapshot = progress.to_dict() # ← freeze engine state
        with _lock:
            latest_progress_snapshot = snapshot
    except Exception as e:
        warn(f"[live] progress update error: {e}")

def start_background_updater() -> None:
    t = threading.Thread(target=_background_status_updater, daemon=True, name="sse-updater")
    t.start()

def stop_background_updater() -> None:
    _updater_stop_event.set()

def _background_status_updater() -> None:
    """Background thread for high-frequency data: progress updates and live gas measurements."""
    global latest_live_data
    while not _updater_stop_event.is_set():
        try:
            if _engine and _engine.is_running():
                result = gasera.acon_proxy()
                if isinstance(result, dict) and result.get("components"):
                    with _lock:
                        progress_snapshot = latest_progress_snapshot.copy() # ← isolate consumer

                    # Timestamp selection
                    if result.get("timestamp") is not None:
                        ts_epoch = result["timestamp"]
                        try:
                            ts = datetime.fromtimestamp(ts_epoch).strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    elif result.get("readable"):
                        ts = result["readable"]
                    else:
                        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                        warn(f"[live] No timestamp from device, using local timestamp: {ts}")

                    live_data = {
                        "timestamp": ts,
                        "phase": progress_snapshot.get("phase"),
                        "channel": progress_snapshot.get("current_channel", 0) + 1,
                        "repeat": progress_snapshot.get("repeat_index", 0),
                        "components": [
                            {
                                "label": c["label"],
                                "ppm": float(c["ppm"]),
                                "color": c["color"],
                                "cas": c["cas"],
                            }
                            for c in result["components"]
                        ],
                    }

                    try:
                        is_new = _engine.on_live_data(live_data)
                        with _lock:
                            latest_live_data = live_data if is_new else {}
                    except Exception as e:
                        warn(f"[live] on_live_data error: {e}")
                else:
                    with _lock:
                        latest_live_data = {}
        except Exception as e:
            error(f"[live] background updater error: {e}")
        time.sleep(SSE_UPDATE_INTERVAL)

def get_live_snapshots() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Get high-frequency data snapshots: progress and live measurements."""
    with _lock:
        return latest_progress_snapshot.copy(), latest_live_data.copy()
