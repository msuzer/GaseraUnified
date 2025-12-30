from flask import Blueprint, jsonify, Response, stream_with_context, request
from gasera.sse.motor_status_service import get_motor_snapshots
from system import services
from system.log_utils import verbose, debug, info, warn, error
from gasera import gas_info
from gasera.sse.utils import SseDeltaTracker
from system.services import engine_service as engine

from gasera.sse.live_status_service import (
    init as live_attach,
    start_background_updater,
    get_live_snapshots,
)

from gasera.sse.device_status_service import (
    get_device_snapshots,
    clear_buzzer_change,
    start_device_status_poller
)

import time, json
from .storage_utils import usb_mounted, get_log_directory, get_free_space, get_total_space, list_log_files, safe_join_in_logdir
import os
from flask import send_file

gasera_bp = Blueprint("gasera", __name__)

# ----------------------------------------------------------------------
# Singleton setup
# ----------------------------------------------------------------------
# Initialize live status service and start updater
live_attach(engine)
services.display_adapter.attach_engine(engine)

start_background_updater()
start_device_status_poller()

# ----------------------------------------------------------------------
# Progress subscription
# ----------------------------------------------------------------------
"""
Live status management moved to gasera.live_status_service
"""

# ----------------------------------------------------------------------
# Gas metadata
# ----------------------------------------------------------------------
@gasera_bp.route("/api/gas_colors")
def gasera_api_gas_colors() -> tuple[Response, int]:
    """Return a mapping of gas labels to their display colors."""
    color_map = gas_info.build_label_to_color_map()
    return jsonify(color_map), 200

# ----------------------------------------------------------------------
# Measurement control
# ----------------------------------------------------------------------
@gasera_bp.route("/api/measurement/start", methods=["POST"])
def start_measurement() -> tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    try:
        services.preferences_service.update_from_dict(data, write_disk=True)
        started, msg = engine.start()

        return jsonify({"ok": started, "message": msg}), 200

    except Exception as e:
        error(f"[MEAS] start failed: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@gasera_bp.route("/api/measurement/repeat", methods=["POST"])
def measurement_repeat():
    ok, msg = engine.trigger_repeat()
    if not ok:
        return jsonify(ok=False, error=msg), 500

    return jsonify(ok=True, message=msg), 200

@gasera_bp.route("/api/measurement/abort", methods=["POST"])
def abort_measurement() -> tuple[Response, int]:
    warn("[MEAS] Abort requested")
    ok, msg = engine.abort()
    if not ok:
        debug(f"[MEAS] abort ignored {msg}")
        return jsonify({"ok": False, "message": msg}), 200

    return jsonify({"ok": True, "message": "Abort initiated"}), 200

@gasera_bp.route("/api/measurement/finish", methods=["POST"])
def finish_measurement() -> tuple[Response, int]:
    info("[MEAS] Finish requested")
    
    ok, msg = engine.finish()
    
    if not ok:
        debug(f"[MEAS] finish ignored {msg}")
        return jsonify({"ok": False, "message": msg}), 200

    return jsonify({"ok": True, "message": "Finish requested"}), 200

# ----------------------------------------------------------------------
# Server-Sent Events
# ----------------------------------------------------------------------
@gasera_bp.route("/api/measurement/events")
def sse_events() -> Response:
    """SSE stream merging high-frequency (progress, live data) and low-frequency (device status) updates."""
    def event_stream():
        last_payload = None
        last_beat = time.monotonic()
        tracker = SseDeltaTracker()

        while True:
            try:
                _progress, _live_data = get_live_snapshots()
                _device_status = get_device_snapshots()
                _motor_status = get_motor_snapshots()

                state = tracker.build(_progress, _live_data, _device_status, _motor_status)
                payload = json.dumps(state, sort_keys=True)
                if payload != last_payload:
                    yield f"data: {payload}\n\n"
                    yield ":\n\n"
                    last_payload = payload
                    last_beat = time.monotonic()

                    # Clear buzzer change flag after successful send
                    if state.get("device_status", {}).get("buzzer", {}).get("_changed"):
                        clear_buzzer_change()
                                        
                    verbose(f"[SSE] sent update: {state}")
                elif time.monotonic() - last_beat > 10:
                    yield ": keep-alive\n\n"
                    last_beat = time.monotonic()
                    verbose("[SSE] sent keep-alive")

                time.sleep(0.5)

            except GeneratorExit:
                debug("[SSE] client disconnected")
                break
            except Exception as e:
                warn(f"[SSE] stream error: {e}")
                time.sleep(1)

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")

# ----------------------------------------------------------------------
# Static file serving for gasera frontend
# ----------------------------------------------------------------------

@gasera_bp.route("/api/logs")
def list_logs():
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 50))

    result = list_log_files(page, page_size)
    result["ok"] = True
    return jsonify(result)

def stream_csv_with_locale(path: str, locale: str):
    # TAB is always used
    out_decimal = "," if locale == "tr-TR" else "."

    def generate():
        with open(path, "r", newline="") as f:
            for line in f:
                if out_decimal == ",":
                    yield line.replace(".", ",")
                else:
                    yield line

    return generate()

@gasera_bp.route("/api/logs/<path:filename>", methods=["GET"])
def download_log(filename):
    try:
        path = safe_join_in_logdir(filename)

        locale = request.args.get("locale")

        # Canonical path: no locale or US locale
        if not locale or locale in ("en-US"):
            return send_file(path, as_attachment=True)

        # Locale requested → export view
        return Response(
            stream_with_context(stream_csv_with_locale(path, locale)),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except FileNotFoundError:
        return jsonify({"ok": False, "error": "File not found"}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@gasera_bp.route("/api/logs/storage", methods=["GET"])
def log_storage_info():
    usb_root = "/media/usb0"
    usb_path = "/media/usb0/logs"
    internal_path = "/data/logs"

    mounted = usb_mounted()

    os.makedirs(internal_path, exist_ok=True)
    if mounted:
        os.makedirs(usb_path, exist_ok=True)

    info = {
        "ok": True,
        "active": "usb0" if mounted else "internal",
        "usb": {
            "mounted": mounted,
            "free": get_free_space(usb_path) if mounted else None,
            "total": get_total_space(usb_root) if mounted else None
        },
        "internal": {
            "free": get_free_space(internal_path),
            "total": get_total_space("/")
        }
    }
    
    return jsonify(info), 200

@gasera_bp.route("/api/logs/delete/<path:filename>", methods=["DELETE"])
def delete_log(filename):
    try:
        path = safe_join_in_logdir(filename)
        os.remove(path)
        return jsonify({"ok": True}), 200
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "File not found"}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@gasera_bp.route("/api/logs/delete_all", methods=["DELETE"])
def delete_all_logs():
    log_dir = get_log_directory()
    try:
        files = [f for f in os.listdir(log_dir) if f.lower().endswith(".csv")]
        for f in files:
            os.remove(os.path.join(log_dir, f))
        return jsonify({"ok": True, "deleted_files": len(files)}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500