# buzzer_facade.py
from typing import Optional


class BuzzerFacade:
    def __init__(self, engine, runtime, preferences):
        self._engine = engine
        self._runtime = runtime
        self._prefs = preferences
        
        # apply persisted preference at init
        from system.preferences import KEY_BUZZER_ENABLED
        enable = self._prefs.get(KEY_BUZZER_ENABLED, True)
        self.enable(enable)

    def enable(self, enable: bool = True):
        if enable:
            self._engine.enable()
        else:
            self._engine.disable()

    def beep(self, duration=0.1):
        if not self._engine.is_enabled():
            return
        self._runtime.submit(self._engine.beep(duration))

    def pattern(self, name):
        if not self._engine.is_enabled():
            return
        self._runtime.submit(self._engine.play(name))

    # ------------------------------------------------------------------------
    # old api
    # ------------------------------------------------------------------------
    def play(self, name: str, repeat: int = 1, now: bool = False, tag: Optional[str] = None) -> None:
        if not self._engine.is_enabled():
            return
        self._runtime.submit(self._engine.play(name, repeat=repeat, now=now, tag=tag))

    def play_morse(self, text: str, repeat: int = 1, now: bool = False, tag: Optional[str] = None, name: Optional[str] = None) -> None:
        if not self._engine.is_enabled():
            return
        self._runtime.submit(self._engine.play_morse(text, repeat=repeat, now=now, tag=tag, name=name))

    def loop(self, name_or_text: str, tag: Optional[str] = None, morse: bool = False) -> None:
        if not self._engine.is_enabled():
            return
        self._runtime.submit(self._engine.loop(name_or_text, tag=tag, morse=morse))

    def cancel(self, tag_or_name: str) -> None:
        self._runtime.submit(self._engine.cancel(tag_or_name))

    def stop_all(self) -> None:
        self._runtime.submit(self._engine.stop_all())
