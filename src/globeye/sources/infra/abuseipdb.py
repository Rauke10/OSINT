"""AbuseIPDB — IP abuse confidence (passive check, no scanning)."""

from __future__ import annotations

from typing import Any, ClassVar

from globeye.core.models import Confidence, Evidence, Finding, RateLimit, Target, TargetType
from globeye.sources.base import PassiveSource, register

_BASE = "https://api.abuseipdb.com/api/v2"


@register
class AbuseIpdbSource(PassiveSource):
    """AbuseIPDB check endpoint for IPv4/IPv6 targets."""

    name: ClassVar[str] = "abuseipdb"
    requires_api_key: ClassVar[bool] = True
    supported_target_types: ClassVar[set[TargetType]] = {TargetType.IP}
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=1, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"api.abuseipdb.com"}

    def api_key(self) -> str | None:
        key = self.ctx.settings.abuseipdb_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, target: Target) -> list[Finding]:
        key = self.api_key()
        if not key:
            return []
        data: Any = await self.get_json(
            f"{_BASE}/check",
            headers={"Key": key, "Accept": "application/json"},
            params={"ipAddress": target.value, "maxAgeInDays": 90, "verbose": ""},
        )
        if not isinstance(data, dict):
            return []
        row = data.get("data")
        if not isinstance(row, dict):
            return []
        score = row.get("abuseConfidenceScore")
        if score is None:
            return []
        return [
            Finding(
                source=self.name,
                target=target.value,
                confidence=Confidence.HIGH if int(score) >= 75 else Confidence.MEDIUM,
                kind="ip_reputation",
                value=f"abuse_score:{score}",
                normalized_data={
                    "abuse_confidence_score": score,
                    "total_reports": row.get("totalReports"),
                    "country_code": row.get("countryCode"),
                    "isp": row.get("isp"),
                    "usage_type": row.get("usageType"),
                    "domain": row.get("domain"),
                    "is_whitelisted": row.get("isWhitelisted"),
                    "last_reported_at": row.get("lastReportedAt"),
                },
                raw_evidence=Evidence(source_url=f"{_BASE}/check"),
            )
        ]
