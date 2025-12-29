# motion/mux_motion.py
class MuxMotion:
    def __init__(self, cmux_gpio, cmux_serial):
        self.cmux_gpio = cmux_gpio
        self.cmux_serial = cmux_serial

    def home(self):
        self.cmux_gpio.home()
        self.cmux_serial.home()

    def step(self, unit_id=None):
        self.cmux_gpio.select_next()
        self.cmux_serial.select_next()
