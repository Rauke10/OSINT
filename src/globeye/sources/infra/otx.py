"""AlienVault OTX — passive DNS (optional API key, higher limits with one)."""

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

_BASE = "https://otx.alienvault.com/api/v1/indicators"


@register
class OtxSource(PassiveSource):
    """OTX passive DNS for domains and IPs."""

    name: ClassVar[str] = "otx"
    requires_api_key: ClassVar[bool] = False
    supported_target_types: ClassVar[set[TargetType]] = {
        TargetType.DOMAIN,
        TargetType.IP,
    }
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=5, per=1, concurrency=2)
    allowed_hosts: ClassVar[set[str]] = {"otx.alienvault.com"}

    def api_key(self) -> str | None:
        key = self.ctx.settings.otx_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, target: Target) -> list[Finding]:
        section = "domain" if target.type is TargetType.DOMAIN else "IPv4"
        headers = {}
        if k := self.api_key():
            headers["X-OTX-API-KEY"] = k
        data: Any = await self.get_json(
            f"{_BASE}/{section}/{target.value}/passive_dns", headers=headers
        )
        if not isinstance(data, dict):
            return []
        seen: set[str] = set()
        findings: list[Finding] = []
        for rec in data.get("passive_dns", []):
            if not isinstance(rec, dict):
                continue
            hostname = str(rec.get("hostname", "")).lower().rstrip(".")
            if not hostname or hostname in seen:
                continue
            seen.add(hostname)
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.MEDIUM,
                    kind="passive_dns",
                    value=hostname,
                    normalized_data={
                        "address": rec.get("address"),
                        "first": rec.get("first"),
                        "last": rec.get("last"),
                    },
                    raw_evidence=Evidence(
                        source_url=f"{_BASE}/{section}/{target.value}/passive_dns"
                    ),
                    graph_node_hint=GraphNodeHint(
                        node_type="domain",
                        node_id=hostname,
                        label=hostname,
                        parent_id=target.value,
                    ),
                )
            )
        return findings
