"""DeHashed — breach records (passive index).

OpSec: GLOBEYE deliberately discards leaked passwords/hashes. Only
**metadata** (which breach database, which field categories were present)
is kept, never the credential values themselves.
"""

from __future__ import annotations

import base64
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

_BASE = "https://api.dehashed.com"
_DROP = {"password", "hashed_password", "raw_record"}


@register
class DehashedSource(PassiveSource):
    """DeHashed search (metadata only — no credential values stored)."""

    name: ClassVar[str] = "dehashed"
    requires_api_key: ClassVar[bool] = True
    supported_target_types: ClassVar[set[TargetType]] = {
        TargetType.EMAIL,
        TargetType.USERNAME,
    }
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=2, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"api.dehashed.com"}

    def _creds(self) -> tuple[str, str] | None:
        email = self.ctx.settings.dehashed_email
        key = self.ctx.settings.dehashed_api_key
        if email and key:
            return email.get_secret_value(), key.get_secret_value()
        return None

    def available(self) -> bool:
        return self._creds() is not None

    def api_key(self) -> str | None:
        creds = self._creds()
        return creds[1] if creds else None

    async def fetch(self, target: Target) -> list[Finding]:
        creds = self._creds()
        if not creds:
            return []
        token = base64.b64encode(f"{creds[0]}:{creds[1]}".encode()).decode()
        field = "email" if target.type is TargetType.EMAIL else "username"
        data: Any = await self.get_json(
            f"{_BASE}/search",
            params={"query": f"{field}:{target.value}"},
            headers={"Accept": "application/json", "Authorization": f"Basic {token}"},
        )
        entries = data.get("entries") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            return []
        findings: list[Finding] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            present = sorted(k for k, v in entry.items() if v and k not in _DROP)
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.MEDIUM,
                    kind="breach_record",
                    value=str(entry.get("database_name", "unknown")),
                    normalized_data={"fields_present": present},
                    raw_evidence=Evidence(source_url=f"{_BASE}/search"),
                )
            )
        return findings
