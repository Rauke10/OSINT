"""Concurrent, passive scan orchestration.

Detects the target, selects applicable & available sources, runs them
concurrently (each with its own rate limiter), deduplicates findings and —
optionally — pivots into newly discovered entities. The pivot walk is
bounded by ``Settings.scan_timeout_seconds``.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from globeye.config import Settings
from globeye.core.context import ScanContext
from globeye.core.models import Finding, ScanResult, SourceStatus, Target
from globeye.core.pivot import _PivotQueue, derive_pivots
from globeye.core.target import detect
from globeye.enrichment.pipeline import EnrichmentPipeline
from globeye.sources.base import PassiveSource, discover_sources


class Orchestrator:
    """Coordinates passive sources for one or more (pivoted) targets."""

    def __init__(self, settings: Settings, ctx: ScanContext | None = None) -> None:
        self.settings = settings
        self.ctx = ctx or ScanContext.create(settings)
        self._source_classes = discover_sources()

    @property
    def source_classes(self) -> list[type[PassiveSource]]:
        return self._source_classes

    def _sources(self) -> list[PassiveSource]:
        return [cls(self.ctx) for cls in self._source_classes]

    async def _scan_one(self, target: Target) -> tuple[list[Finding], list[str], dict[str, str]]:
        used: list[str] = []
        skipped: dict[str, str] = {}
        runnable: list[PassiveSource] = []
        for src in self._sources():
            if not src.applicable(target):
                continue
            if not src.available():
                skipped[src.name] = "missing API key"
                continue
            runnable.append(src)

        async def _run(src: PassiveSource) -> list[Finding]:
            try:
                return await src.fetch(target)
            finally:
                await src.aclose()

        results = await asyncio.gather(*(_run(s) for s in runnable), return_exceptions=True)
        findings: list[Finding] = []
        for src, res in zip(runnable, results, strict=True):
            if isinstance(res, BaseException):
                skipped[src.name] = str(res) or type(res).__name__
                continue
            used.append(src.name)
            findings.extend(res)
        return findings, used, skipped

    @staticmethod
    def _dedup(findings: list[Finding]) -> list[Finding]:
        seen: set[tuple[str, str, str]] = set()
        out: list[Finding] = []
        for f in findings:
            key = f.dedup_key()
            if key in seen:
                continue
            seen.add(key)
            out.append(f)
        return out

    async def _walk(
        self,
        queue: _PivotQueue,
        *,
        pivot: bool,
        max_pivot_depth: int,
    ) -> tuple[list[Finding], list[str], dict[str, str], list[Target]]:
        all_findings: list[Finding] = []
        used: list[str] = []
        skipped: dict[str, str] = {}
        pivoted: list[Target] = []

        while queue:
            current, depth = queue.pop()
            findings, u, s = await self._scan_one(current)
            all_findings.extend(findings)
            for name in u:
                if name not in used:
                    used.append(name)
            for name, reason in s.items():
                skipped.setdefault(name, reason)

            if pivot and depth < max_pivot_depth:
                for pt in derive_pivots(findings):
                    if queue.add(pt, depth + 1):
                        pivoted.append(pt)

        return all_findings, used, skipped, pivoted

    async def scan(
        self,
        raw: str | Target,
        *,
        pivot: bool = False,
        max_pivot_depth: int = 1,
    ) -> ScanResult:
        """Run a full (optionally pivoting) passive scan."""
        target = raw if isinstance(raw, Target) else detect(raw)
        started = datetime.now(UTC)

        async with asyncio.timeout(self.settings.scan_timeout_seconds):
            all_findings, used, skipped, pivoted = await self._walk(
                _PivotQueue(target), pivot=pivot, max_pivot_depth=max_pivot_depth
            )

        deduped = self._dedup(all_findings)
        EnrichmentPipeline(self.settings).run(deduped)
        return ScanResult(
            target=target,
            started_at=started,
            finished_at=datetime.now(UTC),
            sources_used=used,
            sources_skipped=skipped,
            findings=deduped,
            pivoted_targets=pivoted,
        )

    async def health_check(self) -> list[SourceStatus]:
        """Passive health check across every registered source."""
        statuses: list[SourceStatus] = []
        for src in self._sources():
            try:
                statuses.append(await src.health_check())
            finally:
                await src.aclose()
        return statuses
