"""Chaos (ProjectDiscovery) — subdomain dataset (passive, indexed).

Chaos serves a precomputed subdomain dataset; we never resolve the target.
Requires a free API key (sign up with a GitHub account).
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

_BASE = "https://chaos.projectdiscovery.io/api/v1"


@register
class ChaosSource(PassiveSource):
    """ProjectDiscovery Chaos subdomain lookup."""

    name: ClassVar[str] = "chaos"
    requires_api_key: ClassVar[bool] = True
    supported_target_types: ClassVar[set[TargetType]] = {TargetType.DOMAIN}
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=1, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"chaos.projectdiscovery.io"}

    def api_key(self) -> str | None:
        key = self.ctx.settings.chaos_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, target: Target) -> list[Finding]:
        key = self.api_key()
        if not key:
            return []
        data: Any = await self.get_json(
            f"{_BASE}/{target.value}/subdomains",
            headers={"Authorization": key},
        )
        if not isinstance(data, dict):
            return []
        findings: list[Finding] = []
        for label in data.get("subdomains", []):
            fqdn = f"{label}.{target.value}".lower()
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.MEDIUM,
                    kind="subdomain",
                    value=fqdn,
                    raw_evidence=Evidence(source_url=f"{_BASE}/{target.value}/subdomains"),
                    graph_node_hint=GraphNodeHint(
                        node_type="domain",
                        node_id=fqdn,
                        label=fqdn,
                        parent_id=target.value,
                    ),
                )
            )
        return findings
