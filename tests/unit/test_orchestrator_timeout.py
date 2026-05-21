"""The whole scan is bounded by Settings.scan_timeout_seconds."""

from __future__ import annotations

import asyncio
from typing import ClassVar

import pytest

from globeye.config import Settings
from globeye.core.models import Finding, RateLimit, Target, TargetType
from globeye.core.orchestrator import Orchestrator
from globeye.core.target import detect
from globeye.sources.base import PassiveSource


class HangingSource(PassiveSource):
    """A source whose fetch never returns in time."""

    name: ClassVar[str] = "hang"
    requires_api_key: ClassVar[bool] = False
    supported_target_types: ClassVar[set[TargetType]] = {TargetType.DOMAIN}
    rate_limit: ClassVar[RateLimit] = RateLimit()
    allowed_hosts: ClassVar[set[str]] = set()

    async def fetch(self, target: Target) -> list[Finding]:
        await asyncio.sleep(5)
        return []


async def test_scan_times_out_on_a_hanging_source(tmp_path):
    settings = Settings(
        _env_file=None,
        scan_timeout_seconds=0.05,
        cache_enabled=False,
        db_url=f"sqlite:///{tmp_path}/t.db",
    )
    orch = Orchestrator(settings)
    orch._source_classes = [HangingSource]
    with pytest.raises(TimeoutError):
        await orch.scan(detect("example.com"))
