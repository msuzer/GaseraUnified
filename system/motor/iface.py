from typing import Protocol

class MotorInterface(Protocol):
    def move_forward(self) -> None:
        """Move motor forward (CW / extend)."""

    def move_backward(self) -> None:
        """Move motor backward (CCW / retract)."""

    def stop(self) -> None:
        """Stop motor immediately."""

    @property
    def is_moving(self) -> bool:
        """True while motor is running."""
