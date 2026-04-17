"""In-memory event bus for SSE streaming per job.

Each job gets its own asyncio.Queue; SSE endpoints subscribe to consume events.
Includes TTL-based cleanup: queues idle for >5 minutes are automatically removed.
"""
import asyncio
import time
from typing import Any, AsyncGenerator


class EventBus:
    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = {}
        self._last_activity: dict[str, float] = {}
        self._ttl = ttl_seconds
        self._cleanup_task: asyncio.Task | None = None
        self._global_listeners: list = []

    def subscribe(self, job_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._queues.setdefault(job_id, []).append(q)
        self._last_activity[job_id] = time.monotonic()
        return q

    def unsubscribe(self, job_id: str, q: asyncio.Queue) -> None:
        queues = self._queues.get(job_id, [])
        if q in queues:
            queues.remove(q)
        if not queues:
            self._queues.pop(job_id, None)
            self._last_activity.pop(job_id, None)

    async def publish(self, job_id: str, event: dict[str, Any]) -> None:
        self._last_activity[job_id] = time.monotonic()
        for q in self._queues.get(job_id, []):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # drop events on slow consumer

        # Global listeners (for webhooks, etc.)
        for listener in self._global_listeners:
            try:
                asyncio.create_task(listener(job_id, event))
            except Exception:
                pass

    def add_global_listener(self, fn) -> None:
        """Subscribe a coroutine to ALL events from ALL jobs."""
        self._global_listeners.append(fn)

    def remove_global_listener(self, fn) -> None:
        if fn in self._global_listeners:
            self._global_listeners.remove(fn)

    async def stream(self, job_id: str) -> AsyncGenerator[dict, None]:
        q = self.subscribe(job_id)
        try:
            while True:
                event = await q.get()
                yield event
                if event.get("type") in ("done", "error", "stopped"):
                    break
        finally:
            self.unsubscribe(job_id, q)

    # ─── TTL cleanup ───

    async def _cleanup_loop(self) -> None:
        """Periodically remove queues that haven't been active for >TTL seconds."""
        while True:
            await asyncio.sleep(60)
            now = time.monotonic()
            stale = [
                jid
                for jid, last in self._last_activity.items()
                if now - last > self._ttl
            ]
            for jid in stale:
                self._queues.pop(jid, None)
                self._last_activity.pop(jid, None)

    def start_cleanup_task(self) -> None:
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    def stop_cleanup_task(self) -> None:
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()


# Singleton — one bus per process
event_bus = EventBus()
