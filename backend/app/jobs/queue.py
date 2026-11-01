"""In-process async worker queue for DocExtract."""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class JobQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] | None = None
        self._cancelled: set[str] = set()

    @property
    def queue(self) -> asyncio.Queue[str]:
        if self._queue is None:
            self._queue = asyncio.Queue()
        return self._queue

    async def enqueue(self, job_id: str) -> None:
        """Enqueues a job ID for background processing."""
        self._cancelled.discard(job_id)
        await self.queue.put(job_id)
        logger.info(f"Enqueued job {job_id}")

    async def cancel(self, job_id: str) -> None:
        """Marks a job ID as cancelled."""
        self._cancelled.add(job_id)
        logger.info(f"Marked job {job_id} as cancelled")

    async def is_cancelled(self, job_id: str) -> bool:
        """Checks if a job has been cancelled."""
        return job_id in self._cancelled

    async def get_next(self) -> str:
        """Awaits and returns the next job ID to process."""
        return await self.queue.get()

    def task_done(self) -> None:
        self.queue.task_done()


job_queue = JobQueue()
