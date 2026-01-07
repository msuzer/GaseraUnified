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

@motion_bp.post("/home/both")
def motion_home_both():
    try:
        services.motion_actions["0"].home()
        services.motion_actions["1"].home()
        return jsonify({"ok": True})
    except KeyError:
        return jsonify({"error": "Invalid unit"}), 404

@motion_bp.post("/step/both")
def motion_step_both():
    try:
        services.motion_actions["0"].step()
        services.motion_actions["1"].step()
        return jsonify({"ok": True})
    except KeyError:
        return jsonify({"error": "Invalid unit"}), 404

@motion_bp.post("/reset/both")
def motion_reset_both():
    try:
        services.motion_actions["0"].reset()
        services.motion_actions["1"].reset()
        return jsonify({"ok": True})
    except KeyError:
        return jsonify({"error": "Invalid unit"}), 404
