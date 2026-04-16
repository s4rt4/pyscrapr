"""JobManager — tracks running asyncio tasks and exposes stop control.

Replaces the old global `jobs = {}` dict with something testable.
"""
import asyncio
from typing import Callable, Coroutine


class JobManager:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self._stop_flags: dict[str, asyncio.Event] = {}

    def submit(
        self,
        job_id: str,
        runner: Callable[..., Coroutine],
        *args,
        **kwargs,
    ) -> asyncio.Task:
        stop_event = asyncio.Event()
        self._stop_flags[job_id] = stop_event
        task = asyncio.create_task(runner(job_id, stop_event, *args, **kwargs))
        self._tasks[job_id] = task
        task.add_done_callback(lambda _: self._cleanup(job_id))
        return task

    def stop(self, job_id: str) -> bool:
        event = self._stop_flags.get(job_id)
        if event:
            event.set()
            return True
        return False

    def is_running(self, job_id: str) -> bool:
        task = self._tasks.get(job_id)
        return task is not None and not task.done()

    def _cleanup(self, job_id: str) -> None:
        self._tasks.pop(job_id, None)
        self._stop_flags.pop(job_id, None)


# Singleton
job_manager = JobManager()
