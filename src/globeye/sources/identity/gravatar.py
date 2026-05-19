"""Gravatar — public profile bound to an email hash (passive, keyless)."""

from __future__ import annotations

import hashlib
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

_BASE = "https://gravatar.com"


@register
class GravatarSource(PassiveSource):
    """Public Gravatar profile lookup by email hash."""

    name: ClassVar[str] = "gravatar"
    requires_api_key: ClassVar[bool] = False
    supported_target_types: ClassVar[set[TargetType]] = {TargetType.EMAIL}
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=2, per=1, concurrency=2)
    allowed_hosts: ClassVar[set[str]] = {"gravatar.com"}

    async def fetch(self, target: Target) -> list[Finding]:
        # md5 is the Gravatar identifier scheme, not a security primitive.
        digest = hashlib.md5(
            target.value.strip().lower().encode(), usedforsecurity=False
        ).hexdigest()
        data: Any = await self.get_json(f"{_BASE}/{digest}.json")
        entries = data.get("entry") if isinstance(data, dict) else None
        if not entries:
            return []
        entry = entries[0]
        username = str(entry.get("preferredUsername") or entry.get("displayName") or "")
        findings: list[Finding] = [
            Finding(
                source=self.name,
                target=target.value,
                confidence=Confidence.HIGH,
                kind="gravatar_profile",
                value=username or digest,
                normalized_data={
                    "display_name": entry.get("displayName"),
                    "accounts": [
                        a.get("url") for a in entry.get("accounts", []) if isinstance(a, dict)
                    ],
                },
                raw_evidence=Evidence(source_url=f"{_BASE}/{digest}.json"),
            )
        ]
        if username:
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.MEDIUM,
                    kind="username",
                    value=username,
                    raw_evidence=Evidence(source_url=f"{_BASE}/{digest}.json"),
                    graph_node_hint=GraphNodeHint(
                        node_type="username",
                        node_id=username,
                        label=username,
                        parent_id=target.value,
                    ),
                    pivot_target=Target(raw=username, type=TargetType.USERNAME, value=username),
                )
            )
        return findings
