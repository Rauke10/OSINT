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
                "limit": "1000",
            },
        )
        if not isinstance(rows, list) or len(rows) < 2:
            return []
        findings: list[Finding] = []
        seen: set[str] = set()
        for row in rows[1:]:  # row 0 is the header
            if not row:
                continue
            url = str(row[0])
            if url in seen:
                continue
            seen.add(url)
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.LOW,
                    kind="archived_url",
                    value=url,
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
