"""crt.sh — subdomains & certificates from Certificate Transparency logs.

Passive: crt.sh has already indexed the public CT logs. We never resolve or
contact the target; we only query ``crt.sh``.
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

_CRTSH_URL = "https://crt.sh/"


@register
class CrtShSource(PassiveSource):
    """Certificate Transparency lookup via crt.sh."""

    name: ClassVar[str] = "crtsh"
    requires_api_key: ClassVar[bool] = False
    supported_target_types: ClassVar[set[TargetType]] = {TargetType.DOMAIN}
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=2, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"crt.sh"}

    async def fetch(self, target: Target) -> list[Finding]:
        domain = target.value
        rows: Any = await self.get_json(_CRTSH_URL, params={"q": f"%.{domain}", "output": "json"})
        if not isinstance(rows, list):
            return []

        seen: set[str] = set()
        findings: list[Finding] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            names = str(row.get("name_value", "")).split("\n")
            names.append(str(row.get("common_name", "")))
            for name in names:
                sub = name.strip().lower().lstrip("*").lstrip(".").rstrip(".")
                if not sub or "@" in sub or sub in seen:
                    continue
                if sub != domain and not sub.endswith("." + domain):
                    continue
                seen.add(sub)
                findings.append(
                    Finding(
                        source=self.name,
                        target=domain,
                        confidence=Confidence.HIGH,
                        kind="subdomain",
                        value=sub,
                        normalized_data={
                            "issuer": str(row.get("issuer_name", "")),
                            "not_before": row.get("not_before"),
                            "not_after": row.get("not_after"),
                        },
                        raw_evidence=Evidence(
                            source_url=f"{_CRTSH_URL}?q=%.{domain}",
                            raw={"crtsh_id": row.get("id")},
                        ),
                        graph_node_hint=GraphNodeHint(
                            node_type="domain",
                            node_id=sub,
                            label=sub,
                            parent_id=domain,
                        ),
                    )
                )
        return findings
