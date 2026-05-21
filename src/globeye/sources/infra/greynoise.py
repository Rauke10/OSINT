"""GreyNoise Community — is an IP "internet background noise"? (passive).

GreyNoise has already observed/classified the IP from its own sensors; we
never contact the target. Free Community API key required.
"""

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

_BASE = "https://api.greynoise.io/v3/community"


@register
class GreyNoiseSource(PassiveSource):
    """GreyNoise Community IP reputation lookup."""

    name: ClassVar[str] = "greynoise"
    requires_api_key: ClassVar[bool] = True
    supported_target_types: ClassVar[set[TargetType]] = {TargetType.IP}
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=1, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"api.greynoise.io"}

    def api_key(self) -> str | None:
        key = self.ctx.settings.greynoise_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, target: Target) -> list[Finding]:
        key = self.api_key()
        if not key:
            return []
        data: Any = await self.get_json(f"{_BASE}/{target.value}", headers={"key": key})
        if not isinstance(data, dict) or "classification" not in data:
            return []
        classification = str(data.get("classification", "unknown"))
        return [
            Finding(
                source=self.name,
                target=target.value,
                confidence=Confidence.MEDIUM,
                kind="reputation",
                value=f"{target.value}: {classification}",
                normalized_data={
                    "classification": classification,
                    "name": data.get("name"),
                    "noise": data.get("noise"),
                    "riot": data.get("riot"),
                    "last_seen": data.get("last_seen"),
                },
                raw_evidence=Evidence(source_url=f"{_BASE}/{target.value}"),
            )
        ]
