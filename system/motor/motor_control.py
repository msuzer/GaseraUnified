import time
from threading import Thread, RLock
from system.preferences import prefs, KEY_MOTOR_TIMEOUT
from system.motor.bank import MotorBank

DEFAULT_MOTOR_TIMEOUT = 10          # seconds

class MotorController:
    def __init__(self, motors: MotorBank):
        self.motors = motors
        self.timeout_sec = prefs.get_int(KEY_MOTOR_TIMEOUT, DEFAULT_MOTOR_TIMEOUT)
        self._state = {
            "0": {"status": "idle", "direction": None},
            "1": {"status": "idle", "direction": None}
        }
        self._lock = {"0": RLock(), "1": RLock()}
        self._threads = {}

    def set_timeout(self, seconds):
        self.timeout_sec = int(seconds or DEFAULT_MOTOR_TIMEOUT)

    def get_timeout(self):
        return self.timeout_sec

    def start(self, motor_id: str, direction: str):
        lock = self._lock[motor_id]
        with lock:
            if self._state[motor_id]["status"] == "moving":
                print(f"[WARN] Motor {motor_id} already moving")
                return

            if direction == "cw":
                self.motors[motor_id].move_forward()
            else:
                self.motors[motor_id].move_backward()

            self._state[motor_id] = {"status": "moving", "direction": direction}
            print(f"[MOTOR] Started motor {motor_id} {direction.upper()}")

            if motor_id in self._threads and self._threads[motor_id].is_alive():
                return
            
            t = Thread(target=self._monitor, args=(motor_id, direction), daemon=True)
            t.start()
            self._threads[motor_id] = t

    def stop(self, motor_id: str):
        lock = self._lock[motor_id]
        with lock:
            self.motors[motor_id].stop()            
            if self._state[motor_id]["status"] == "moving":
                direction = self._state[motor_id]["direction"]
                self._state[motor_id] = {
                    "status": "user_stop",
                    "direction": direction,
                }
                print(f"[MOTOR] Stopped motor {motor_id} manually.")
                
    def start_both(self, direction: str):
        self.start("0", direction)
        self.start("1", direction)
        
    def stop_both(self):
        self.stop("0")
        self.stop("1")

    def _monitor(self, motor_id: str, direction: str):
        start = time.time()
        while time.time() - start < self.timeout_sec:
            state = self._state[motor_id]
            if state["status"] != "moving":
                return

            time.sleep(0.5)
        
        with self._lock[motor_id]:
            self.motors[motor_id].stop()
            self._state[motor_id] = {
                "status": "timeout",
                "direction": direction,
            }

    def state(self, motor_id: str, as_string=False):
        s = self._state.get(motor_id, {"status": "unknown", "direction": None})
        if as_string:
            return f"{s['status']} {s['direction']}" if s["direction"] else s["status"]
        return s

    def is_done(self, motor_id: str) -> bool:
        return self._state[motor_id]["status"] in ["limit", "timeout", "user_stop", "idle"]

    def are_both_done(self) -> bool:
        return self.is_done("0") and self.is_done("1")
