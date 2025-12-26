# pin_assignments.py

# PC14 and PC15 starts as inputs upon boot up, thus outputting HIGH, do not use them as output pins.
# PI16 works on armbian but marked as 'used' on debian bookworm, do not use it.

# -------------------------------
# Hardware profiles
# -------------------------------

_PIN_PROFILES = {
    "relay_board": {
        "BUZZER_PIN":  "PH2",
        "TRIGGER_PIN": "PC10",
    },
    "optocoupler_board": {
        "BUZZER_PIN":  "PH8",
        "TRIGGER_PIN": "PH9",
    },
}

# -------------------------------
# Default profile
# -------------------------------

_DEFAULT_PROFILE = "relay_board"

# -------------------------------
# Public pins (resolved)
# -------------------------------

_PROFILE = _DEFAULT_PROFILE

def select_profile(name: str):
    global _PROFILE, BUZZER_PIN, TRIGGER_PIN
    if name not in _PIN_PROFILES:
        raise ValueError(f"Unknown pin profile: {name}")
    _PROFILE = name

    BUZZER_PIN  = _PIN_PROFILES[_PROFILE]["BUZZER_PIN"]
    TRIGGER_PIN = _PIN_PROFILES[_PROFILE]["TRIGGER_PIN"]


# initialize defaults
BUZZER_PIN  = _PIN_PROFILES[_PROFILE]["BUZZER_PIN"]
TRIGGER_PIN = _PIN_PROFILES[_PROFILE]["TRIGGER_PIN"]

# -------------------------------
# Fixed pin assignments
# -------------------------------
OC1_PIN = "PC8"
OC2_PIN = "PC5"
OC3_PIN = "PC11"
OC4_PIN = "PH3"
OC5_PIN = "PH2"

BOARD_IN1_PIN = "PC15"
BOARD_IN2_PIN = "PC14"
BOARD_IN3_PIN = "PH8"
BOARD_IN4_PIN = "PC7"
BOARD_IN5_PIN = "PH6"
BOARD_IN6_PIN = "PH9"

MOTOR0_CW_PIN = "PH3"
MOTOR0_CCW_PIN = "PC11"
MOTOR1_CW_PIN = "PC5"
MOTOR1_CCW_PIN = "PC8"
