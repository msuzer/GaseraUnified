from flask import Blueprint, jsonify
from system import services
from system.log_utils import error

motion_bp = Blueprint("motion", __name__)

@motion_bp.post("/take/<action>/<unit_id>")
def motion_command(action, unit_id):
    if action not in ("home", "step", "reset"):
        return jsonify({"error": "Invalid action"}), 400
    if unit_id not in ("0", "1", "both"):
        return jsonify({"error": "Invalid unit_id"}), 400

    def _perform(uid: str) -> bool:
        action_obj = services.motion_actions.get(uid)
        if action_obj is None:
            return False
        try:
            if action == "home":
                action_obj.home()
            elif action == "step":
                action_obj.step()
            elif action == "reset":
                action_obj.reset()
            return True
        except Exception as exc:
            # Log and treat as a failed action instead of crashing the request
            error(f"[MOTION] Action '{action}' failed for unit {uid}: {exc}")
            return False

    if unit_id == "both":
        done_any = False
        for uid in ("0", "1"):
            # Attempt action for each unit and continue on failure
            if _perform(uid):
                done_any = True
        if not done_any:
            return jsonify({"error": "No action performed"}), 503
        return jsonify({"ok": True})

    if _perform(unit_id):
        return jsonify({"ok": True})
    return jsonify({"error": "No action defined"}), 503
