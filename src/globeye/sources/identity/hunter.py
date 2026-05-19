"""Hunter.io — email patterns / known emails for a domain (passive index)."""

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

_BASE = "https://api.hunter.io/v2"


@register
class HunterSource(PassiveSource):
    """Hunter.io domain search."""

    name: ClassVar[str] = "hunter"
    requires_api_key: ClassVar[bool] = True
    supported_target_types: ClassVar[set[TargetType]] = {TargetType.DOMAIN}
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=2, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"api.hunter.io"}

    def api_key(self) -> str | None:
        key = self.ctx.settings.hunter_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, target: Target) -> list[Finding]:
        key = self.api_key()
        if not key:
            return []
        data: Any = await self.get_json(
            f"{_BASE}/domain-search",
            params={"domain": target.value, "api_key": key, "limit": "100"},
        )
        block = data.get("data", {}) if isinstance(data, dict) else {}
        findings: list[Finding] = []
        pattern = block.get("pattern")
        if pattern:
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.MEDIUM,
                    kind="email_pattern",
                    value=str(pattern),
                    raw_evidence=Evidence(source_url=f"{_BASE}/domain-search"),
                )
            )
        for email in block.get("emails", []):
            if not isinstance(email, dict):
                continue
            addr = str(email.get("value", "")).lower()
            if not addr:
                continue
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.MEDIUM,
                    kind="email",
                    value=addr,
                    normalized_data={
                        "type": email.get("type"),
                        "confidence": email.get("confidence"),
                    },
                    raw_evidence=Evidence(source_url=f"{_BASE}/domain-search"),
                    graph_node_hint=GraphNodeHint(
                        node_type="email",
                        node_id=addr,
                        label=addr,
                        parent_id=target.value,
                    ),
                    pivot_target=Target(raw=addr, type=TargetType.EMAIL, value=addr),
                )
            )
        return findings
