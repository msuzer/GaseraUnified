# mux/mux_vici_uma.py
import time
import serial

from system.mux.iface import MuxInterface
from system.mux.protocol_vici_uma import ViciUMAProtocol
from system.log_utils import error


class ViciUMAMux(MuxInterface):
    """
    VICI UMA over USB–RS232 adapter (/dev/ttyUSBx)
    """

    def __init__(self, port,
                 *, baudrate=9600,
                 max_channels=16,
                 settle_ms=200):
        self.max = max_channels
        self._pos = 0
        self.settle = settle_ms / 1000 # ms to s
        self.error = False

        try :
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=0.3,
                write_timeout=0.3,
            )

            # one-time safe init
            self._send(ViciUMAProtocol.set_mode_multiposition())
            self._send(ViciUMAProtocol.set_num_positions(max_channels))
            # self._send(ViciUMAProtocol.home())

        except Exception as e:
            error(f"❌ VICI UMA failed on {port}: {e}")
            self.error = True

        self._pos = 0

    @property
    def position(self):
        return self._pos

    def _send(self, payload: bytes):
        if self.error:
            return

        self.ser.reset_input_buffer()
        self.ser.write(payload)
        self.ser.flush()
        time.sleep(self.settle)

    def home(self):
        if not self.error:
            self._send(ViciUMAProtocol.home())

        self._pos = 0
        return self._pos

    def select_next(self):
        if not self.error:
            if self._pos + 1 >= self.max:
                return self.home()

            self._send(ViciUMAProtocol.step_forward())

        self._pos += 1
        return self._pos
