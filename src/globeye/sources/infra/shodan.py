"""Shodan — services & DNS that Shodan already indexed (no scanning by us)."""

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

_BASE = "https://api.shodan.io"


@register
class ShodanSource(PassiveSource):
    """Shodan host & DNS lookup (passive: Shodan scanned, not us)."""

    name: ClassVar[str] = "shodan"
    requires_api_key: ClassVar[bool] = True
    supported_target_types: ClassVar[set[TargetType]] = {
        TargetType.IP,
        TargetType.DOMAIN,
    }
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=1, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"api.shodan.io"}

    def api_key(self) -> str | None:
        key = self.ctx.settings.shodan_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, target: Target) -> list[Finding]:
        key = self.api_key()
        if not key:
            return []
        if target.type is TargetType.IP:
            return await self._host(target, key)
        return await self._domain(target, key)

    async def _host(self, target: Target, key: str) -> list[Finding]:
        data: Any = await self.get_json(f"{_BASE}/shodan/host/{target.value}", params={"key": key})
        if not isinstance(data, dict):
            return []
        findings: list[Finding] = []
        for svc in data.get("data", []):
            if not isinstance(svc, dict):
                continue
            port = svc.get("port")
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.HIGH,
                    kind="service",
                    value=f"{target.value}:{port}/{svc.get('transport', 'tcp')}",
                    normalized_data={
                        "port": port,
                        "product": svc.get("product"),
                        "hostnames": svc.get("hostnames"),
                    },
                    raw_evidence=Evidence(source_url=f"{_BASE}/shodan/host/{target.value}"),
                )
            )
        return findings

    async def _domain(self, target: Target, key: str) -> list[Finding]:
        data: Any = await self.get_json(f"{_BASE}/dns/domain/{target.value}", params={"key": key})
        if not isinstance(data, dict):
            return []
        findings: list[Finding] = []
        for rec in data.get("data", []):
            if not isinstance(rec, dict) or rec.get("type") not in {"A", "AAAA", "CNAME"}:
                continue
            sub = rec.get("subdomain")
            fqdn = f"{sub}.{target.value}" if sub else target.value
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.MEDIUM,
                    kind="subdomain",
                    value=fqdn,
                    normalized_data={"type": rec.get("type"), "value": rec.get("value")},
                    raw_evidence=Evidence(source_url=f"{_BASE}/dns/domain/{target.value}"),
                    graph_node_hint=GraphNodeHint(
                        node_type="domain", node_id=fqdn, label=fqdn, parent_id=target.value
                    ),
                )
            )
        return findings
