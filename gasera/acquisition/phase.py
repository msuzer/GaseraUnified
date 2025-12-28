
class Phase:
    IDLE = "IDLE"           # engine not active / ready
    ARMED = "READY"         # motor: waiting for trigger
    HOMING = "HOMING"       # actuator homing
    SWITCHING = "SWITCHING" # mux switching or actuator movement
    PAUSED = "PAUSED"       # intentional pause/dwell
    MEASURING = "MEASURING" # gas sampling
    ABORTED = "ABORTED"     # aborted by user/error
