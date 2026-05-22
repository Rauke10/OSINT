"""Concurrent, passive scan orchestration.

Detects the target, selects applicable & available sources, runs them
concurrently (each with its own rate limiter), deduplicates findings and —
optionally — pivots into newly discovered entities.
"""

from __future__ import annotations

import asyncio
import ipaddress
from datetime import UTC, datetime

from globeye.config import Settings
from globeye.core.context import ScanContext
from globeye.core.models import Finding, ScanResult, SourceRun, SourceStatus, Target
from globeye.core.pivot import derive_pivots
from globeye.core.target import detect
from globeye.enrichment.geoip import GeoIPEnricher
from globeye.enrichment.reputation import assess
from globeye.services.source_errors import (
    error_type_from_reason,
    format_source_error,
    skip_reason_to_status,
)
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

    async def _scan_one(
        self,
        target: Target,
        *,
        source_names: frozenset[str] | None = None,
    ) -> tuple[list[Finding], list[str], dict[str, str], list[SourceRun]]:
        used: list[str] = []
        skipped: dict[str, str] = {}
        runs: list[SourceRun] = []
        runnable: list[PassiveSource] = []
        for src in self._sources():
            if source_names is not None and src.name not in source_names:
                continue
            if not src.applicable(target):
                continue
            if not src.available():
                reason = "missing API key — configure in .env"
                skipped[src.name] = reason
                now = datetime.now(UTC)
                runs.append(
                    SourceRun(
                        name=src.name,
                        status="missing_key",
                        message=reason,
                        started_at=now,
                        finished_at=now,
                        latency_ms=0,
                        error_type="missing_key",
                    )
                )
                continue
            runnable.append(src)

        async def _run(
            src: PassiveSource,
        ) -> tuple[PassiveSource, list[Finding] | BaseException, datetime, datetime]:
            started = datetime.now(UTC)
            try:
                findings = await src.fetch(target)
                return src, findings, started, datetime.now(UTC)
            except BaseException as exc:
                return src, exc, started, datetime.now(UTC)
            finally:
                await src.aclose()

        results = await asyncio.gather(*(_run(s) for s in runnable))
        findings: list[Finding] = []
        for src, res, started, finished in results:
            latency = int((finished - started).total_seconds() * 1000)
            if isinstance(res, BaseException):
                reason = format_source_error(res)
                skipped[src.name] = reason
                runs.append(
                    SourceRun(
                        name=src.name,
                        status=skip_reason_to_status(reason),
                        findings_count=0,
                        started_at=started,
                        finished_at=finished,
                        latency_ms=latency,
                        message=reason,
                        error_type=error_type_from_reason(reason),
                    )
                )
                continue
            count = len(res)
            used.append(src.name)
            findings.extend(res)
            runs.append(
                SourceRun(
                    name=src.name,
                    status="used" if count else "no_results",
                    findings_count=count,
                    started_at=started,
                    finished_at=finished,
                    latency_ms=latency,
                    message=None if count else "Queried successfully, no findings",
                )
            )
        return findings, used, skipped, runs

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

    async def scan(
        self,
        raw: str | Target,
        *,
        pivot: bool = False,
        max_pivot_depth: int = 1,
        source_names: frozenset[str] | None = None,
    ) -> ScanResult:
        """Run a full (optionally pivoting) passive scan."""
        target = raw if isinstance(raw, Target) else detect(raw)
        started = datetime.now(UTC)

        all_findings: list[Finding] = []
        all_runs: list[SourceRun] = []
        used: list[str] = []
        skipped: dict[str, str] = {}
        pivoted: list[Target] = []
        seen: set[tuple[str, str]] = {(target.type.value, target.value)}
        queue: list[tuple[Target, int]] = [(target, 0)]

        while queue:
            current, depth = queue.pop(0)

            findings, u, s, runs = await self._scan_one(current, source_names=source_names)
            all_findings.extend(findings)
            all_runs.extend(runs)
            for name in u:
                if name not in used:
                    used.append(name)
            for name, reason in s.items():
                skipped.setdefault(name, reason)

            if pivot and depth < max_pivot_depth:
                for pt in derive_pivots(findings):
                    pkey = (pt.type.value, pt.value)
                    if pkey in seen:
                        continue
                    seen.add(pkey)
                    pivoted.append(pt)
                    queue.append((pt, depth + 1))

        deduped = self._dedup(all_findings)
        self._enrich(deduped)
        return ScanResult(
            target=target,
            started_at=started,
            finished_at=datetime.now(UTC),
            sources_used=used,
            sources_skipped=skipped,
            findings=deduped,
            pivoted_targets=pivoted,
            source_runs=all_runs,
        )

    @staticmethod
    def _finding_ip(finding: Finding) -> str | None:
        for candidate in (finding.target, finding.value.split(":")[0]):
            try:
                return str(ipaddress.ip_address(candidate))
            except ValueError:
                continue
        return None

    def _enrich(self, findings: list[Finding]) -> None:
        geo = GeoIPEnricher(self.settings.geoip_city_db, self.settings.geoip_asn_db)
        try:
            for f in findings:
                f.normalized_data["reputation"] = assess(f)
                ip = self._finding_ip(f)
                if ip is None or not geo.enabled:
                    continue
                geo_data: dict[str, object] = {"ip": ip}
                if city := geo.city(ip):
                    geo_data.update(city)
                if asn := geo.asn(ip):
                    geo_data["asn"] = asn
                if len(geo_data) > 1:
                    f.normalized_data["geo"] = geo_data
        finally:
            geo.close()

    async def health_check(self) -> list[SourceStatus]:
        """Passive health check across every registered source."""
        statuses: list[SourceStatus] = []
        for src in self._sources():
            try:
                statuses.append(await src.health_check())
            finally:
                await src.aclose()
        return statuses
