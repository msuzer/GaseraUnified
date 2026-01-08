import os, time, json
from flask import Blueprint, jsonify, Response, stream_with_context, request, send_file

from system import services
from gasera import gas_info
from gasera.sse.utils import SseDeltaTracker
from system.log_utils import verbose, debug, info, warn, error
from .storage_utils import usb_mounted, get_log_directory, get_free_space, get_total_space, list_log_files, safe_join_in_logdir

gasera_bp = Blueprint("gasera", __name__)

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
    services.preferences_service.update_from_dict(data, write_disk=True)

    ok, msg = services.engine_actions.start()
    return jsonify({"ok": ok, "message": msg}), 200

@gasera_bp.route("/api/measurement/repeat", methods=["POST"])
def measurement_repeat() -> tuple[Response, int]:
    ok, msg = services.engine_actions.repeat()
    return jsonify({"ok": ok, "message": msg}), 200

@gasera_bp.route("/api/measurement/abort", methods=["POST"])
def abort_measurement() -> tuple[Response, int]:
    ok, msg = services.engine_actions.abort()
    return jsonify({"ok": ok, "message": msg}), 200

@gasera_bp.route("/api/measurement/finish", methods=["POST"])
def finish_measurement() -> tuple[Response, int]:
    ok, msg = services.engine_actions.finish()
    return jsonify({"ok": ok, "message": msg}), 200

@gasera_bp.route("/api/measurement/config", methods=["GET"])
def get_measurement_config() -> tuple[Response, int]:
    from system.preferences import KEY_MEASUREMENT_START_MODE
    from gasera.acquisition.base import MeasurementStartMode

    mode = services.preferences_service.get(
        KEY_MEASUREMENT_START_MODE,
        MeasurementStartMode.PER_CYCLE
    )

    return jsonify({"ok": True, KEY_MEASUREMENT_START_MODE: mode}), 200

@gasera_bp.route("/api/measurement/config", methods=["POST"])
def update_measurement_config() -> tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    
    from gasera.acquisition.base import MeasurementStartMode
    from system.preferences import KEY_MEASUREMENT_START_MODE
    mode = data.get(KEY_MEASUREMENT_START_MODE)
    
    try:
        mode = MeasurementStartMode(mode)
    except Exception:
        return jsonify({
            "ok": False,
            "error": f"{KEY_MEASUREMENT_START_MODE} must be "
                    f"'{MeasurementStartMode.PER_TASK}' or "
                    f"'{MeasurementStartMode.PER_CYCLE}'"
        }), 400

    services.preferences_service.update_from_dict(
        {KEY_MEASUREMENT_START_MODE: mode},
        write_disk=True
    )

    info(f"[MEAS] {KEY_MEASUREMENT_START_MODE} set to {mode}")

    return jsonify({"ok": True, KEY_MEASUREMENT_START_MODE: mode}), 200

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
                _progress, _live_data = services.live_status_service.get_live_snapshots()
                _device_status = services.device_status_service.get_device_snapshots()
                _motion_status = services.motion_status_service.get_motion_snapshots()

                state = tracker.build(_progress, _live_data, _device_status, _motion_status)
                payload = json.dumps(state, sort_keys=True)
                if payload != last_payload:
                    yield f"data: {payload}\n\n"
                    yield ":\n\n"
                    last_payload = payload
                    last_beat = time.monotonic()

                    # Clear buzzer change flag after successful send
                    if state.get("device_status", {}).get("buzzer", {}).get("_changed"):
                        services.device_status_service.clear_buzzer_change()
                                        
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
    get_segments = request.args.get("segments", "").lower() in ("1", "true", "yes")

    result = list_log_files(page, page_size, get_segments=get_segments)
    result["ok"] = True
    result["segments"] = get_segments
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
    get_segments = request.args.get("segments", "").lower() in ("1", "true", "yes")
    log_dir = get_log_directory(temp_dir=get_segments)
    path = safe_join_in_logdir(log_dir, filename)
    locale = request.args.get("locale")

    try:
        if get_segments and not filename.lower().endswith(".tsv"):
            return Response(
                "Segment files can only be downloaded in the default format (TSV).",
                status=400,
                mimetype="text/plain"
            )

        if not get_segments and not filename.lower().endswith(".csv"):
            return Response(
                "Log files can only be downloaded in the default format (CSV).",
                status=400,
                mimetype="text/plain"
            )
        
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

@gasera_bp.route("/api/logs/delete/<path:filename>", methods=["DELETE"])
def delete_log(filename):
    get_segments = request.args.get("segments", "").lower() in ("1", "true", "yes")
    log_dir = get_log_directory(temp_dir=get_segments)
    path = safe_join_in_logdir(log_dir, filename)

    try:
        if get_segments and not filename.lower().endswith(".tsv"):
            jsonify({"ok": False, "error": "Segment files can only be deleted in the default format (TSV)."}), 400

        if not get_segments and not filename.lower().endswith(".csv"):
            return jsonify({"ok": False, "error": "Log files can only be deleted in the default format (CSV)."}), 400

        os.remove(path)
        return jsonify({"ok": True, "deleted_file": filename, "segments": get_segments}), 200
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "File not found"}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@gasera_bp.route("/api/logs/delete_all", methods=["DELETE"])
def delete_all_logs():
    get_segments = request.args.get("segments", "").lower() in ("1", "true", "yes")
    log_dir = get_log_directory(temp_dir=get_segments)
    ext = ".tsv" if get_segments else ".csv"

    try:
        files = [f for f in os.listdir(log_dir) if f.lower().endswith(ext)]
        for f in files:
            os.remove(os.path.join(log_dir, f))
        return jsonify({"ok": True, "deleted_files": len(files)}), 200
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
