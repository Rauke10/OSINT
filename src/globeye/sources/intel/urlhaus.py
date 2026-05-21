"""URLhaus (abuse.ch) — malicious URLs known for a host (passive index).

URLhaus is a curated, already-indexed feed of malicious URLs. We query its
API, never the target. Keyless; an optional abuse.ch ``Auth-Key`` is sent
when configured.
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

_HOST_API = "https://urlhaus-api.abuse.ch/v1/host/"


@register
class UrlhausSource(PassiveSource):
    """URLhaus malicious-URL lookup for a host."""

    name: ClassVar[str] = "urlhaus"
    requires_api_key: ClassVar[bool] = False
    supported_target_types: ClassVar[set[TargetType]] = {
        TargetType.DOMAIN,
        TargetType.IP,
    }
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=1, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"urlhaus-api.abuse.ch"}

    def _headers(self) -> dict[str, str]:
        key = self.ctx.settings.abusech_auth_key
        return {"Auth-Key": key.get_secret_value()} if key else {}

    async def fetch(self, target: Target) -> list[Finding]:
        data: Any = await self.get_json(
            _HOST_API,
            method="POST",
            data={"host": target.value},
            headers=self._headers(),
        )
        if not isinstance(data, dict) or data.get("query_status") != "ok":
            return []
        findings: list[Finding] = []
        for entry in data.get("urls", []):
            if not isinstance(entry, dict):
                continue
            url = str(entry.get("url", ""))
            if not url:
                continue
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.HIGH,
                    kind="malicious_url",
                    value=url,
                    normalized_data={
                        "threat": entry.get("threat"),
                        "url_status": entry.get("url_status"),
                        "date_added": entry.get("date_added"),
                    },
                    raw_evidence=Evidence(source_url=_HOST_API),
                    graph_node_hint=GraphNodeHint(
                        node_type="url",
                        node_id=url,
                        label=url[:80],
                        parent_id=target.value,
                    ),
                )
            )
        return findings
