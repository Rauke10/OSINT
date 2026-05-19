"""Orchestrator: selection, dedup, pivot, skip handling."""

from __future__ import annotations

from typing import ClassVar

from globeye.core.models import (
    Confidence,
    Finding,
    RateLimit,
    Target,
    TargetType,
)
from globeye.core.orchestrator import Orchestrator
from globeye.core.target import detect
from globeye.sources.base import PassiveSource


class FakeSource(PassiveSource):
    name: ClassVar[str] = "fake"
    requires_api_key: ClassVar[bool] = False
    supported_target_types: ClassVar[set[TargetType]] = {
        TargetType.DOMAIN,
        TargetType.EMAIL,
    }
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1000, per=1, concurrency=4)
    allowed_hosts: ClassVar[set[str]] = set()

    async def fetch(self, target: Target) -> list[Finding]:
        if target.type is TargetType.DOMAIN:
            pivot = Target(
                raw="found@example.com",
                type=TargetType.EMAIL,
                value="found@example.com",
            )
            base = Finding(
                source=self.name,
                target=target.value,
                confidence=Confidence.HIGH,
                kind="email",
                value="found@example.com",
                pivot_target=pivot,
            )
            return [base, base.model_copy()]  # duplicate -> must dedup
        return [
            Finding(
                source=self.name,
                target=target.value,
                confidence=Confidence.LOW,
                kind="note",
                value=f"pivoted:{target.value}",
            )
        ]


class KeyedSource(FakeSource):
    name: ClassVar[str] = "keyed"
    requires_api_key: ClassVar[bool] = True

    def api_key(self) -> str | None:
        return None


async def test_scan_dedup_and_no_pivot(settings):
    orch = Orchestrator(settings)
    orch._source_classes = [FakeSource, KeyedSource]
    result = await orch.scan(detect("example.com"))

    assert [f.value for f in result.findings] == ["found@example.com"]
    assert "fake" in result.sources_used
    assert result.sources_skipped.get("keyed") == "missing API key"
    assert result.pivoted_targets == []
    assert result.duration_seconds >= 0


async def test_scan_with_pivot(settings):
    orch = Orchestrator(settings)
    orch._source_classes = [FakeSource]
    result = await orch.scan("example.com", pivot=True)

    kinds = {f.kind for f in result.findings}
    assert "email" in kinds
    assert "note" in kinds
    assert [t.value for t in result.pivoted_targets] == ["found@example.com"]


async def test_scan_enriches_findings_with_reputation(settings):
    orch = Orchestrator(settings)
    orch._source_classes = [FakeSource]
    result = await orch.scan(detect("example.com"))
    assert all("reputation" in f.normalized_data for f in result.findings)


async def test_health_check(settings):
    orch = Orchestrator(settings)
    orch._source_classes = [FakeSource, KeyedSource]
    statuses = {s.name: s for s in await orch.health_check()}
    assert statuses["fake"].available is True
    assert statuses["keyed"].available is False
