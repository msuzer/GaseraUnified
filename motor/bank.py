# motor/bank.py  (new, tiny helper)
class MotorBank:
    def __init__(self, motors: dict[str, object]):
        self._motors = motors

    def get(self, motor_id: str):
        return self._motors[motor_id]
