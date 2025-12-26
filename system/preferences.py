import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List
from system.log_utils import debug, info, warn, error

# --- Channel State Constants ---
class ChannelState:
    """Channel state values for include_channels preference."""
    INACTIVE = 0
    ACTIVE = 1
    SAMPLED = 2

# --- Preference Keys ---
VALID_PREF_KEYS = [
        "measurement_duration",
        "pause_seconds",
        "repeat_count",
        "include_channels",
        "track_visibility",
        "buzzer_enabled",
        "online_mode_enabled",
        "simulator_enabled",
        "motor_timeout",
    ]

KEY_MEASUREMENT_DURATION  = VALID_PREF_KEYS[0]
KEY_PAUSE_SECONDS         = VALID_PREF_KEYS[1]
KEY_REPEAT_COUNT          = VALID_PREF_KEYS[2]
KEY_INCLUDE_CHANNELS      = VALID_PREF_KEYS[3]
KEY_TRACK_VISIBILITY      = VALID_PREF_KEYS[4]
KEY_BUZZER_ENABLED        = VALID_PREF_KEYS[5]
KEY_ONLINE_MODE_ENABLED   = VALID_PREF_KEYS[6]
KEY_SIMULATOR_ENABLED     = VALID_PREF_KEYS[7]
KEY_MOTOR_TIMEOUT         = VALID_PREF_KEYS[8]

class Preferences:
    """
    Simple JSON-based preference store with auto-initialization
    and callback support.
    """

    DEFAULT_INCLUDE_COUNT = 31  # default number of channels to include

    def __init__(self, filename: str = "config/user_prefs.json"):
        self.file = Path(filename)
        self.data: Dict[str, Any] = {}
        self._callbacks: Dict[str, List[Callable[[str, Any], None]]] = {}
        self._load()

        # Ensure include_channels mask exists
        if KEY_INCLUDE_CHANNELS not in self.data:
            self.data[KEY_INCLUDE_CHANNELS] = [ChannelState.ACTIVE] * self.DEFAULT_INCLUDE_COUNT
            self.save()

    # ------------------------------------------------------------------
    # Core file ops
    # ------------------------------------------------------------------

    def _load(self):
        if not self.file.exists():
            warn(f"[PREFS] file not found, will create {self.file}")
            self.data = {}
            return
        try:
            with open(self.file, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception as e:
            error(f"[PREFS] load failed: {e}")
            self.data = {}

    def save(self):
        """Public save method."""
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            error(f"[PREFS] save failed: {e}")

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self.data.get(key, default))
        except Exception:
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        try:
            return float(self.data.get(key, default))
        except Exception:
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.data.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        return bool(value)

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def update_from_dict(self, d: Dict[str, Any], write_disk: bool = False) -> List[str]:
        """Update preferences from dictionary.
        
        Args:
            d: Dictionary of key-value pairs to update
            write_disk: If True, saves to disk. If False, updates memory only.
        """
        updated = []
        for k, v in d.items():
            if k not in VALID_PREF_KEYS:
                continue
            
            # Check if value actually changed before adding to updated list
            if k not in self.data or self.data[k] != v:
                self.data[k] = v
                updated.append(k)
            else:
                debug(f"[PREFS] skipping {k}, value unchanged")
        
        if updated:
            debug(f"[PREFS] updating keys: {updated}")
            if write_disk:
                self.save()
            for k in updated:
                self._notify(k, self.data[k])
        
        return updated

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def register_callback(self, key, cb: Callable[[str, Any], None]):
            if key not in self._callbacks:
                self._callbacks[key] = []
            self._callbacks[key].append(cb)

    def _notify(self, key: str, value: Any):
        if key in self._callbacks:
            for cb in self._callbacks[key]:
                try:
                    cb(value)
                except Exception as e:
                    print(f"[WARN] Callback for '{key}' failed: {e}")

    # ------------------------------------------------------------------

    def as_dict(self) -> Dict[str, Any]:
        return dict(self.data)

# Singleton
prefs = Preferences()
