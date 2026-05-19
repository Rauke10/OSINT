"""SecurityTrails — passive DNS / historical data (free tier)."""

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

_BASE = "https://api.securitytrails.com/v1"


@register
class SecurityTrailsSource(PassiveSource):
    """SecurityTrails subdomain & passive-DNS lookup."""

    name: ClassVar[str] = "securitytrails"
    requires_api_key: ClassVar[bool] = True
    supported_target_types: ClassVar[set[TargetType]] = {TargetType.DOMAIN}
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=2, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"api.securitytrails.com"}

    def api_key(self) -> str | None:
        key = self.ctx.settings.securitytrails_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, target: Target) -> list[Finding]:
        key = self.api_key()
        if not key:
            return []
        headers = {"APIKEY": key, "Accept": "application/json"}
        data: Any = await self.get_json(
            f"{_BASE}/domain/{target.value}/subdomains",
            params={"children_only": "false"},
            headers=headers,
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
                    raw_evidence=Evidence(source_url=f"{_BASE}/domain/{target.value}/subdomains"),
                    graph_node_hint=GraphNodeHint(
                        node_type="domain",
                        node_id=fqdn,
                        label=fqdn,
                        parent_id=target.value,
                    ),
                )
            )
        return findings
