"""DiskCache + AsyncRateLimiter behaviour."""

from __future__ import annotations

import asyncio
import time

from globeye.core.models import RateLimit
from globeye.utils.cache import DiskCache
from globeye.utils.ratelimit import AsyncRateLimiter


def test_cache_roundtrip(tmp_path):
    c = DiskCache(tmp_path, ttl_seconds=60)
    assert c.get("ns", "k") is None
    c.set("ns", "k", {"a": 1})
    assert c.get("ns", "k") == {"a": 1}


def test_cache_expiry(tmp_path):
    c = DiskCache(tmp_path, ttl_seconds=0)
    c.set("ns", "k", "v")
    time.sleep(0.01)
    assert c.get("ns", "k") is None


def test_cache_disabled(tmp_path):
    c = DiskCache(tmp_path, ttl_seconds=60, enabled=False)
    c.set("ns", "k", "v")
    assert c.get("ns", "k") is None


def test_cache_corrupt_file_is_ignored(tmp_path):
    c = DiskCache(tmp_path, ttl_seconds=60)
    c.set("ns", "k", "v")
    path = c._path("ns", "k")
    path.write_text("not-json", encoding="utf-8")
    assert c.get("ns", "k") is None


async def test_rate_limiter_spaces_requests():
    limiter = AsyncRateLimiter(RateLimit(rate=1, per=0.05, concurrency=1))
    start = asyncio.get_running_loop().time()
    async with limiter:
        pass
    async with limiter:
        pass
    assert asyncio.get_running_loop().time() - start >= 0.05
