"""urlscan.io — URLs already scanned by urlscan (passive search).

We query urlscan's *search* index of scans other people submitted; we never
submit a scan of the target ourselves. The API key is optional (it only
raises the rate limit).
"""

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

_SEARCH = "https://urlscan.io/api/v1/search/"


@register
class UrlscanSource(PassiveSource):
    """Search urlscan.io for existing scans of a domain or IP."""

    name: ClassVar[str] = "urlscan"
    requires_api_key: ClassVar[bool] = False
    supported_target_types: ClassVar[set[TargetType]] = {
        TargetType.DOMAIN,
        TargetType.IP,
    }
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=2, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"urlscan.io"}

    def api_key(self) -> str | None:
        key = self.ctx.settings.urlscan_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, target: Target) -> list[Finding]:
        field = "domain" if target.type is TargetType.DOMAIN else "ip"
        headers = {}
        if k := self.api_key():
            headers["API-Key"] = k
        data: Any = await self.get_json(
            _SEARCH,
            params={"q": f"{field}:{target.value}", "size": "100"},
            headers=headers,
        )
        results = data.get("results", []) if isinstance(data, dict) else []
        seen: set[str] = set()
        findings: list[Finding] = []
        for row in results:
            page = row.get("page", {}) if isinstance(row, dict) else {}
            url = str(page.get("url", ""))
            if not url or url in seen:
                continue
            seen.add(url)
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.LOW,
                    kind="archived_url",
                    value=url,
                    normalized_data={"scan_id": row.get("_id")},
                    raw_evidence=Evidence(source_url=_SEARCH),
                    graph_node_hint=GraphNodeHint(
                        node_type="url",
                        node_id=url,
                        label=url[:80],
                        parent_id=target.value,
                    ),
                )
            )
        return findings
