"""Have I Been Pwned — breach membership for an email (passive index)."""

from __future__ import annotations

from typing import Any, ClassVar

from globeye.core.models import (
    Confidence,
    Evidence,
    Finding,
    RateLimit,
    Target,
    TargetType,
)
from globeye.sources.base import PassiveSource, register

_BASE = "https://haveibeenpwned.com/api/v3"


@register
class HibpSource(PassiveSource):
    """HIBP breached-account lookup."""

    name: ClassVar[str] = "hibp"
    requires_api_key: ClassVar[bool] = True
    supported_target_types: ClassVar[set[TargetType]] = {TargetType.EMAIL}
    # HIBP free tier: 1 request / 1.5 s.
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=1.6, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"haveibeenpwned.com"}

    def api_key(self) -> str | None:
        key = self.ctx.settings.hibp_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, target: Target) -> list[Finding]:
        key = self.api_key()
        if not key:
            return []
        data: Any = await self.get_json(
            f"{_BASE}/breachedaccount/{target.value}",
            params={"truncateResponse": "false"},
            headers={"hibp-api-key": key},
        )
        if not isinstance(data, list):  # None == 404 == not found in any breach
            return []
        findings: list[Finding] = []
        for breach in data:
            if not isinstance(breach, dict):
                continue
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.HIGH,
                    kind="breach",
                    value=str(breach.get("Name", "unknown")),
                    normalized_data={
                        "title": breach.get("Title"),
                        "breach_date": breach.get("BreachDate"),
                        "data_classes": breach.get("DataClasses"),
                        "is_verified": breach.get("IsVerified"),
                    },
                    raw_evidence=Evidence(source_url=f"{_BASE}/breachedaccount/<redacted>"),
                )
            )
        return findings
