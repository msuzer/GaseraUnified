# mux/iface.py
from abc import ABC, abstractmethod


class MuxInterface(ABC):
    def __init__(self, *, max_channels: int = 16, settle_ms: int = 0):
        self.max = max_channels
        self._pos = 0
        self.settle = settle_ms / 1000
        self.error = False

    @property
    def position(self) -> int:
        return self._pos

    @abstractmethod
    def home(self) -> int: ...

    @abstractmethod
    def select_next(self) -> int: ...
