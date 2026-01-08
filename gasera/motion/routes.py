from flask import Blueprint, jsonify
from system import services

motion_bp = Blueprint("motion", __name__)

@motion_bp.post("/home/<unit_id>")
def motion_home(unit_id):
    try:
        action = services.motion_actions.get(unit_id)
        if action is not None:
            action.home()
            return jsonify({"ok": True})
        else:
            return jsonify({"error": "No action defined"}), 503
    except KeyError:
        return jsonify({"error": "Invalid unit"}), 404

@motion_bp.post("/step/<unit_id>")
def motion_step(unit_id):
    try:
        action = services.motion_actions.get(unit_id)
        if action is not None:
            action.step()
            return jsonify({"ok": True})
        else:
            return jsonify({"error": "No action defined"}), 503
    except KeyError:
        return jsonify({"error": "Invalid unit"}), 404

@motion_bp.post("/reset/<unit_id>")
def motion_reset(unit_id):
    try:
        action = services.motion_actions.get(unit_id)
        if action is not None:
            action.reset()
            return jsonify({"ok": True})
        else:
            return jsonify({"error": "No action defined"}), 503
    except KeyError:
        return jsonify({"error": "Invalid unit"}), 404

@motion_bp.post("/home/both")
def motion_home_both():
    try:
        action0 = services.motion_actions.get("0")
        action1 = services.motion_actions.get("1")
        if action0 is not None:
            action0.home()

        if action1 is not None:
            action1.home()
            
        if action0 is None and action1 is None:
            return jsonify({"error": "No action defined"}), 503
        
        return jsonify({"ok": True})
    except KeyError:
        return jsonify({"error": "Invalid unit"}), 404

@motion_bp.post("/step/both")
def motion_step_both():
    try:
        action0 = services.motion_actions.get("0")
        action1 = services.motion_actions.get("1")
        
        if action0 is not None:
            action0.step()
        
        if action1 is not None:
            action1.step()
            
        if action0 is None and action1 is None:
            return jsonify({"error": "No action defined"}), 503
        
        return jsonify({"ok": True})        
    except KeyError:
        return jsonify({"error": "Invalid unit"}), 404

@motion_bp.post("/reset/both")
def motion_reset_both():
    try:
        action0 = services.motion_actions.get("0")
        action1 = services.motion_actions.get("1")

        if action0 is not None:
            action0.reset()

        if action1 is not None:
            action1.reset()
            
        if action0 is None and action1 is None:
            return jsonify({"error": "No action defined"}), 503
        
        return jsonify({"ok": True})
    except KeyError:
        return jsonify({"error": "Invalid unit"}), 404
