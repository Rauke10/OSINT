"""ThreatFox (abuse.ch) — indicators of compromise (passive index).

ThreatFox is a curated IoC database. We query its API, never the target.
Keyless; an optional abuse.ch ``Auth-Key`` is sent when configured.
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

_API = "https://threatfox-api.abuse.ch/api/v1/"


@register
class ThreatFoxSource(PassiveSource):
    """ThreatFox IoC search."""

    name: ClassVar[str] = "threatfox"
    requires_api_key: ClassVar[bool] = False
    supported_target_types: ClassVar[set[TargetType]] = {
        TargetType.DOMAIN,
        TargetType.IP,
        TargetType.EMAIL,
    }
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=1, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"threatfox-api.abuse.ch"}

    def _headers(self) -> dict[str, str]:
        key = self.ctx.settings.abusech_auth_key
        return {"Auth-Key": key.get_secret_value()} if key else {}

    async def fetch(self, target: Target) -> list[Finding]:
        data: Any = await self.get_json(
            _API,
            method="POST",
            json_body={"query": "search_ioc", "search_term": target.value},
            headers=self._headers(),
        )
        if not isinstance(data, dict) or data.get("query_status") != "ok":
            return []
        rows = data.get("data", [])
        findings: list[Finding] = []
        for entry in rows if isinstance(rows, list) else []:
            if not isinstance(entry, dict):
                continue
            ioc = str(entry.get("ioc", ""))
            if not ioc:
                continue
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.HIGH,
                    kind="ioc",
                    value=ioc,
                    normalized_data={
                        "ioc_type": entry.get("ioc_type"),
                        "threat_type": entry.get("threat_type"),
                        "malware": entry.get("malware_printable"),
                        "first_seen": entry.get("first_seen"),
                    },
                    raw_evidence=Evidence(source_url=_API),
                )
            )
        return findings
