"""Per-source asynchronous rate limiting.

Combines a concurrency :class:`asyncio.Semaphore` with a minimum spacing
between consecutive requests so we always respect a source's published
rate limit.
"""

from __future__ import annotations

import asyncio
from types import TracebackType

from globeye.core.models import RateLimit


class AsyncRateLimiter:
    """Bound concurrency and enforce a minimum interval between requests."""

    def __init__(self, limit: RateLimit) -> None:
        self._sem = asyncio.Semaphore(max(1, limit.concurrency))
        self._min_interval = limit.min_interval
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def acquire(self) -> None:
        await self._sem.acquire()
        async with self._lock:
            loop = asyncio.get_running_loop()
            wait = self._min_interval - (loop.time() - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = loop.time()

    def release(self) -> None:
        self._sem.release()

    async def __aenter__(self) -> AsyncRateLimiter:
        await self.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()
