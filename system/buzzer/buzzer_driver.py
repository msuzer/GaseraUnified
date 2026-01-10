class BuzzerDriver:
    def __init__(self, gpio_service, pin: int):
        self._gpio = gpio_service
        self._pin = pin

    def on(self):
        self._gpio.set(self._pin)

    def off(self):
        self._gpio.reset(self._pin)
