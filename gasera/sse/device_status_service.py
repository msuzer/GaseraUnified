from __future__ import annotations

import threading
import time
from typing import Dict, Any

from system.log_utils import debug
from system.preferences import KEY_BUZZER_ENABLED
from system import services
from gasera.storage_utils import check_usb_change


class DeviceStatusService:
    """Encapsulates device status polling and snapshot access.

    Usage: instantiate after `system.services` wiring, then call
    `register_callbacks()` and `start_poller()` from the app init.
    """

    def __init__(self, poll_interval: float = 2.0):
        self._latest_device_status: Dict[str, Any] = {
            "connection": {"online": False},
            "usb": {"mounted": False},
            "buzzer": {"enabled": False},
            "gasera": {},
        }

        self._latest_usb_mounted: bool = False
        self._buzzer_change_pending: bool | None = None

        self._lock = threading.Lock()

        self._device_poll_interval = poll_interval
        self._poller_thread: threading.Thread | None = None

    # Public accessors
    def get_device_snapshots(self) -> Dict[str, Any]:
        with self._lock:
            online = self._latest_device_status.get("gasera", {}).get("online", False)
            self._latest_device_status["connection"] = {"online": online}
            self._latest_device_status["usb"] = {"mounted": self._latest_usb_mounted}

            enabled = False
            prefs = services.preferences_service
            if prefs is not None:
                enabled = bool(prefs.get(KEY_BUZZER_ENABLED, False))

            buz = {"enabled": enabled}
            if self._buzzer_change_pending is not None:
                buz["_changed"] = True
            self._latest_device_status["buzzer"] = buz

            return self._latest_device_status.copy()

    def get_latest_gasera_status(self) -> Dict[str, Any]:
        with self._lock:
            return self._latest_device_status.get("gasera", {}).copy()

    def clear_buzzer_change(self) -> None:
        with self._lock:
            self._buzzer_change_pending = None

    # Internal updaters
    def _update_usb_status(self) -> None:
        try:
            mounted, _ = check_usb_change()
        except Exception:
            mounted = self._latest_usb_mounted

        with self._lock:
            self._latest_usb_mounted = mounted

    def _update_gasera_status(self) -> None:
        try:
            dev_status = services.gasera_controller.get_device_status()
        except Exception:
            with self._lock:
                self._latest_device_status["gasera"] = {"online": False, "error": True}
            return

        if not dev_status or dev_status.error:
            with self._lock:
                self._latest_device_status["gasera"] = {"online": False, "error": True}
            return

        status = {
            "online": True,
            "status": dev_status.status_str,
            "status_code": dev_status.status_code,
        }

        with self._lock:
            self._latest_device_status["gasera"] = status

    def _update_gasera_phase(self) -> None:
        with self._lock:
            status = self._latest_device_status.get("gasera", {}).copy()

        online = status.get("online", False)
        code = status.get("status_code")

        if online and code == 5:
            try:
                meas_status = services.gasera_controller.get_measurement_status()
                phase = (
                    meas_status.description
                    if meas_status and not meas_status.error
                    else "unknown"
                )
            except Exception:
                phase = "unknown"

            with self._lock:
                self._latest_device_status["gasera"]["phase"] = phase

    # Poller lifecycle
    def start_poller(self) -> None:
        if self._poller_thread and self._poller_thread.is_alive():
            return

        def _loop():
            while True:
                try:
                    self._update_usb_status()
                    self._update_gasera_status()
                    time.sleep(self._device_poll_interval)
                    self._update_gasera_phase()
                    time.sleep(self._device_poll_interval)
                except Exception:
                    time.sleep(self._device_poll_interval)

        self._poller_thread = threading.Thread(
            target=_loop, name="DeviceStatusPoller", daemon=True
        )
        self._poller_thread.start()

    # Preference callbacks
    def _on_buzzer_change(self, key: str, value: Any) -> None:
        if key == KEY_BUZZER_ENABLED:
            with self._lock:
                self._buzzer_change_pending = bool(value)
                debug(f"[DEVICE] Buzzer change detected: {value}")

    def register_callbacks(self) -> None:
        prefs = services.preferences_service
        if prefs is None:
            return
        prefs.register_callback(KEY_BUZZER_ENABLED, self._on_buzzer_change)


# -----------------------------------------------------------------------------
# Module-level compatibility functions (delegate to instance in services)
# -----------------------------------------------------------------------------

def _get_service() -> DeviceStatusService | None:
    svc = getattr(services, "device_status_service", None)
    return svc


def get_device_snapshots() -> Dict[str, Any]:
    svc = _get_service()
    if svc is None:
        return {}
    return svc.get_device_snapshots()


def get_latest_gasera_status() -> Dict[str, Any]:
    svc = _get_service()
    if svc is None:
        return {}
    return svc.get_latest_gasera_status()


def clear_buzzer_change() -> None:
    svc = _get_service()
    if svc is None:
        return
    svc.clear_buzzer_change()


def start_device_status_poller() -> None:
    svc = _get_service()
    if svc is None:
        return
    svc.start_poller()

