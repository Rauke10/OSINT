"""EmailRep — reputation of an email address (passive aggregation).

EmailRep aggregates already-public signals about an address. The API key
is optional (it only raises the rate limit).
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

_BASE = "https://emailrep.io"


@register
class EmailRepSource(PassiveSource):
    """EmailRep.io email reputation lookup."""

    name: ClassVar[str] = "emailrep"
    requires_api_key: ClassVar[bool] = False
    supported_target_types: ClassVar[set[TargetType]] = {TargetType.EMAIL}
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=3, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"emailrep.io"}

    def api_key(self) -> str | None:
        key = self.ctx.settings.emailrep_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, target: Target) -> list[Finding]:
        headers = {"User-Agent": self.ctx.settings.user_agent}
        if k := self.api_key():
            headers["Key"] = k
        data: Any = await self.get_json(f"{_BASE}/{target.value}", headers=headers)
        if not isinstance(data, dict) or "reputation" not in data:
            return []
        details = data.get("details", {}) or {}
        return [
            Finding(
                source=self.name,
                target=target.value,
                confidence=(Confidence.HIGH if data.get("suspicious") else Confidence.LOW),
                kind="email_reputation",
                value=f"{target.value}: {data.get('reputation', 'none')}",
                normalized_data={
                    "reputation": data.get("reputation"),
                    "suspicious": data.get("suspicious"),
                    "references": data.get("references"),
                    "credentials_leaked": details.get("credentials_leaked"),
                    "data_breach": details.get("data_breach"),
                },
                raw_evidence=Evidence(source_url=f"{_BASE}/<redacted>"),
            )
        ]
