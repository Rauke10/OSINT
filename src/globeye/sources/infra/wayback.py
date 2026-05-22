"""Wayback Machine — historical URLs from the Internet Archive CDX API."""

from __future__ import annotations

from typing import Any, ClassVar

from globeye.core.models import (
    Confidence,
    Evidence,
    Finding,
    GraphNodeHint,
    RateLimit,
    Target,
    TargetType,
)
from globeye.sources.base import PassiveSource, register

_CDX = "https://web.archive.org/cdx/search/cdx"
# Max rows requested from CDX per scan (passive); all unique URLs become findings + entities.
CDX_FETCH_LIMIT = 200
WAYBACK_FINDINGS_PER_SCAN = CDX_FETCH_LIMIT
# Legacy name: only live-check batch uses 25 (see url_live_check.MAX_BATCH_URLS).
WAYBACK_ENTITY_LIMIT = 25


@register
class WaybackSource(PassiveSource):
    """Archived URLs for a domain (Internet Archive)."""

    name: ClassVar[str] = "wayback"
    requires_api_key: ClassVar[bool] = False
    supported_target_types: ClassVar[set[TargetType]] = {TargetType.DOMAIN}
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=2, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"web.archive.org"}

    async def fetch(self, target: Target) -> list[Finding]:
        rows: Any = await self.get_json(
            _CDX,
            params={
                "url": f"{target.value}/*",
                "output": "json",
                "fl": "original",
                "collapse": "urlkey",
                "limit": str(CDX_FETCH_LIMIT),
            },
        )
        if not isinstance(rows, list) or len(rows) < 2:
            return []

        urls: list[str] = []
        seen: set[str] = set()
        for row in rows[1:]:
            if not row:
                continue
            url = str(row[0])
            if url in seen:
                continue
            seen.add(url)
            urls.append(url)

        total = len(urls)
        operational_urls = urls[:WAYBACK_FINDINGS_PER_SCAN]
        findings: list[Finding] = []

        if total > 0:
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.LOW,
                    kind="wayback_summary",
                    value=f"{total} URLs históricas archivadas",
                    normalized_data={
                        "total_urls": total,
                        "operational_urls": len(operational_urls),
                        "truncated": total > WAYBACK_FINDINGS_PER_SCAN,
                        "cdx_fetch_limit": CDX_FETCH_LIMIT,
                        "live_check_batch_limit": WAYBACK_ENTITY_LIMIT,
                    },
                    raw_evidence=Evidence(source_url=_CDX),
                )
            )

        for idx, url in enumerate(operational_urls):
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.LOW,
                    kind="archived_url",
                    value=url,
                    normalized_data={
                        "wayback_index": idx,
                        "wayback_total": total,
                        "wayback_truncated": total > WAYBACK_FINDINGS_PER_SCAN,
                    },
                    raw_evidence=Evidence(source_url=_CDX),
                    graph_node_hint=GraphNodeHint(
                        node_type="url",
                        node_id=url,
                        label=url[:80],
                        parent_id=target.value,
                    ),
                )
            )
        return findings
