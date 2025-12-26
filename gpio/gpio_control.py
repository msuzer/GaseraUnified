import threading
import gpiod

# Common pin map
PIN_MAP = {
    "PC1": 65, "PC5": 69, "PC6": 70, "PC7": 71, "PC8": 72, "PC9": 73, "PC10": 74, "PC11": 75, "PC14": 78, "PC15": 79,
    "PH2": 226, "PH3": 227, "PH4": 228, "PH5": 229, "PH6": 230, "PH7": 231, "PH8": 232, "PH9": 233,
    "PI6": 262, "PI16": 272
}


def find_gpiochip_by_line_count(target_lines=288, fallback="gpiochip0"):
    """Finds the correct gpiochip by checking number of lines."""
    for i in range(2):  # Increase range if needed
        chip_name = f"gpiochip{i}"
        try:
            chip = gpiod.Chip(chip_name)
            if chip.num_lines() == target_lines:
                return chip_name
        except OSError:
            continue
    return fallback

class GPIOController:
    """Real GPIO controller using gpiod on Linux."""
    def __init__(self):
        chip_name = find_gpiochip_by_line_count(288)
        self.chip = gpiod.Chip(chip_name)
        self.pin_states = {}

    def read(self, pin_name):
        line_num = PIN_MAP[pin_name]
        line = self.chip.get_line(line_num)
        line.request(consumer="gpio-read", type=gpiod.LINE_REQ_DIR_IN)
        val = line.get_value()
        self.pin_states[line_num] = val
        line.release()
        return val

    def set(self, pin_name):
        line_num = PIN_MAP[pin_name]
        line = self.chip.get_line(line_num)
        line.request(consumer="gpio-set", type=gpiod.LINE_REQ_DIR_OUT, default_vals=[1])
        self.pin_states[line_num] = 1
        line.release()
        return 1

    def reset(self, pin_name):
        line_num = PIN_MAP[pin_name]
        line = self.chip.get_line(line_num)
        line.request(consumer="gpio-reset", type=gpiod.LINE_REQ_DIR_OUT, default_vals=[0])
        self.pin_states[line_num] = 0
        line.release()
        return 0
    
    # --------------------------------------------------------------
    # Event-based watcher (edge detection)
    # --------------------------------------------------------------
    def watch(self, pin_name, callback, edge="both"):
        """
        Starts a background thread that calls callback(pin_name, value)
        whenever the pin changes. Uses hardware edge detection.
        """
        line_num = PIN_MAP[pin_name]
        line = self.chip.get_line(line_num)

        if edge == "rising":
            req_type = gpiod.LINE_REQ_EV_RISING_EDGE
        elif edge == "falling":
            req_type = gpiod.LINE_REQ_EV_FALLING_EDGE
        else:
            req_type = gpiod.LINE_REQ_EV_BOTH_EDGES

        line.request(consumer="gpio-watch", type=req_type)

        def monitor():
            while True:
                if line.event_wait(sec=1):
                    evt = line.event_read()
                    value = line.get_value()
                    callback(pin_name, value)

        t = threading.Thread(target=monitor, daemon=True)
        t.start()
        return t

# Global instance
gpio = GPIOController()

"""
Initialize GPIOs with defined startup directions and levels.
"""

# Import input pins
from gpio.pin_assignments import (TRIGGER_PIN, BOARD_IN1_PIN, BOARD_IN2_PIN, BOARD_IN3_PIN, BOARD_IN4_PIN, BOARD_IN5_PIN, BOARD_IN6_PIN)

# Import output pins
from gpio.pin_assignments import (BUZZER_PIN, OC1_PIN, OC2_PIN, OC3_PIN, OC4_PIN, OC5_PIN, MOTOR0_CW_PIN, MOTOR0_CCW_PIN, MOTOR1_CW_PIN, MOTOR1_CCW_PIN)

# Output pins initialized LOW
output_pins = [BUZZER_PIN, OC1_PIN, OC2_PIN, OC3_PIN, OC4_PIN, OC5_PIN, MOTOR0_CW_PIN, MOTOR0_CCW_PIN, MOTOR1_CW_PIN, MOTOR1_CCW_PIN]
for pin in output_pins:
    gpio.reset(pin)
