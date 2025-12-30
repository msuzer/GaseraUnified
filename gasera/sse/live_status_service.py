# live_status_service.py
from __future__ import annotations
import threading
import time
from datetime import datetime
from typing import Dict, Any, Tuple

from system.log_utils import warn, error
from system import services
from gasera.acquisition.base import Progress, Phase


class LiveStatusService:
    """High-frequency live data service capturing progress and live measurements."""

    def __init__(self, update_interval: float = 25.0):
        self.latest_progress_snapshot: Dict[str, Any] = {"phase": Phase.IDLE, "current_channel": 0, "repeat_index": 0}
        self.latest_live_data: Dict[str, Any] = {}

        self._lock = threading.Lock()
        self._update_interval = update_interval
        self._updater_stop_event = threading.Event()
        self._updater_thread: threading.Thread | None = None
        self._engine = None

    def attach_engine(self, engine) -> None:
        self._engine = engine
        try:
            engine.subscribe(self._on_progress)
        except Exception:
            # subscribe may not be present on all engine implementations
            pass

    def _on_progress(self, progress: Progress) -> None:
        try:
            snapshot = progress.to_dict()
            with self._lock:
                self.latest_progress_snapshot = snapshot
        except Exception as e:
            warn(f"[live] progress update error: {e}")

    def start_background_updater(self) -> None:
        if self._updater_thread and self._updater_thread.is_alive():
            return

        def _background_status_updater() -> None:
            while not self._updater_stop_event.is_set():
                try:
                    if self._engine and getattr(self._engine, "is_running", lambda: False)():
                        result = services.gasera_controller.acon_proxy()
                        if isinstance(result, dict) and result.get("components"):
                            with self._lock:
                                progress_snapshot = self.latest_progress_snapshot.copy()

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
                                is_new = self._engine.on_live_data(live_data)
                                with self._lock:
                                    self.latest_live_data = live_data if is_new else {}
                            except Exception as e:
                                warn(f"[live] on_live_data error: {e}")
                        else:
                            with self._lock:
                                self.latest_live_data = {}
                except Exception as e:
                    error(f"[live] background updater error: {e}")
                time.sleep(self._update_interval)

        self._updater_thread = threading.Thread(target=_background_status_updater, daemon=True, name="sse-updater")
        self._updater_thread.start()

    def stop_background_updater(self) -> None:
        self._updater_stop_event.set()

    def get_live_snapshots(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        with self._lock:
            return self.latest_progress_snapshot.copy(), self.latest_live_data.copy()


# -----------------------------------------------------------------------------
# Module-level delegates to instance in system.services
# -----------------------------------------------------------------------------

def _get_service() -> LiveStatusService | None:
    return getattr(services, "live_status_service", None)


def init(engine) -> None:
    svc = _get_service()
    if svc is None:
        return
    svc.attach_engine(engine)


def start_background_updater() -> None:
    svc = _get_service()
    if svc is None:
        return
    svc.start_background_updater()


def stop_background_updater() -> None:
    svc = _get_service()
    if svc is None:
        return
    svc.stop_background_updater()


def get_live_snapshots() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    svc = _get_service()
    if svc is None:
        return {}, {}
    return svc.get_live_snapshots()
