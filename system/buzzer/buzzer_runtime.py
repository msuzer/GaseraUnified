import asyncio
import threading

from system.log_utils import warn

class BuzzerRuntime:
    def __init__(self):
        self._loop = None
        self._thread = None
        self._ready = threading.Event()
        self._lock = threading.Lock()

    def start(self, engine):
        with self._lock:
            if self._thread:
                return

            self._thread = threading.Thread(
                target=self._run_loop,
                args=(engine,),
                daemon=True,
                name="BuzzerRuntime",
            )
            self._thread.start()
            self._ready.wait()

    def _run_loop(self, engine):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self._loop.create_task(engine._worker())
        self._ready.set()

        try:
            self._loop.run_forever()
        finally:
            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.close()

    def submit(self, coro):
        if not self._loop:
            warn("Buzzer runtime not started")
            return
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    def shutdown(self, engine):
        with self._lock:
            if not self._loop:
                return

            async def _shutdown():
                await engine.shutdown()
                self._loop.stop()

            asyncio.run_coroutine_threadsafe(_shutdown(), self._loop)
            self._thread.join(timeout=2)

            self._loop = None
