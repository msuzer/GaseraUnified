from flask import Blueprint, jsonify
from system import services

motion_bp = Blueprint("motion", __name__)

@motion_bp.post("/home/<unit_id>")
def motion_home(unit_id):
    try:
        services.motion_actions[unit_id].home()
        return jsonify({"ok": True})
    except KeyError:
        return jsonify({"error": "Invalid unit"}), 404

@motion_bp.post("/step/<unit_id>")
def motion_step(unit_id):
    try:
        services.motion_actions[unit_id].step()
        return jsonify({"ok": True})
    except KeyError:
        return jsonify({"error": "Invalid unit"}), 404

@motion_bp.post("/reset/<unit_id>")
def motion_reset(unit_id):
    try:
        services.motion_actions[unit_id].reset()
        return jsonify({"ok": True})
    except KeyError:
        return jsonify({"error": "Invalid unit"}), 404
