# motor/bank.py  (new, tiny helper)
class MotorBank:
    def __init__(self, motors: dict[str, object]):
        self._motors = motors

    def get(self, motor_id: str):
        return self._motors[motor_id]

    def __getitem__(self, motor_id):
        return self._motors[motor_id]

    def items(self):
        return self._motors.items()

    def values(self):
        return self._motors.values()

    def keys(self):
        return self._motors.keys()
