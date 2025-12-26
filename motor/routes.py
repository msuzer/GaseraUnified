from flask import Blueprint, request, jsonify
from system.log_utils import debug, info
from system.services import motor_controller as motor

motor_bp = Blueprint("motor", __name__)

# motor state: idle, moving, timeout, limit, user_stop, unknown
@motor_bp.route("/status", methods=["GET"])
def motor_status():
    if motor is None:
        return jsonify({
            "error": "Motor control not supported",
            "code": "SERVICE_UNAVAILABLE"
        }), 503
    
    state0 = motor.state("0")
    state1 = motor.state("1")
        
    debug(f"[MOTOR STATUS] Motor 0: {state0}, Motor 1: {state1}")
    
    return jsonify({
        "0": state0,
        "1": state1
    })

@motor_bp.route("/jog/<action>", methods=["POST"])
def motor_jog(action):
    if motor is None:
        return jsonify({
            "error": "Motor control not supported",
            "code": "SERVICE_UNAVAILABLE"
        }), 503
    
    motor_id = request.form.get("motor_id")
    direction = request.form.get("direction")

    if motor_id not in {"0", "1"} or direction not in {"cw", "ccw"}:
        return jsonify({"error": "Invalid motor or direction"}), 400

    try:
        if action == "start":
            motor.start(motor_id, direction)
        elif action == "stop":
            motor.stop(motor_id)
        else:
            return jsonify({"error": "Unknown action"}), 400
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@motor_bp.route("/jog/both/<action>", methods=["POST"])
def motor_jog_both(action):
    if motor is None:
        return jsonify({
            "error": "Motor control not supported",
            "code": "SERVICE_UNAVAILABLE"
        }), 503

    try:
        if action == "start":
            direction = request.form.get("direction")
            if direction not in {"cw", "ccw"}:
                return jsonify({"error": "Invalid direction"}), 400
            motor.start_both(direction)

        elif action == "stop":
            motor.stop_both()

        else:
            return jsonify({"error": "Unknown action"}), 400

        return jsonify({"ok": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 400
