"""Pastebin exposure — discovered via the Google Custom Search index.

Passive: we query Google's index (a third party), not pastebin or the
target. Requires a Google CSE key + engine id (cx).
"""

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

_BASE = "https://www.googleapis.com/customsearch/v1"


@register
class PastebinSource(PassiveSource):
    """Public pastes mentioning the target, via Google CSE."""

    name: ClassVar[str] = "pastebin"
    requires_api_key: ClassVar[bool] = True
    supported_target_types: ClassVar[set[TargetType]] = {
        TargetType.DOMAIN,
        TargetType.EMAIL,
    }
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=1, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"www.googleapis.com"}

    def _creds(self) -> tuple[str, str] | None:
        key = self.ctx.settings.google_cse_key
        cx = self.ctx.settings.google_cse_cx
        if key and cx:
            return key.get_secret_value(), cx.get_secret_value()
        return None

    def available(self) -> bool:
        return self._creds() is not None

    def api_key(self) -> str | None:
        creds = self._creds()
        return creds[0] if creds else None

    async def fetch(self, target: Target) -> list[Finding]:
        creds = self._creds()
        if not creds:
            return []
        key, cx = creds
        data: Any = await self.get_json(
            _BASE,
            params={
                "key": key,
                "cx": cx,
                "q": f'site:pastebin.com "{target.value}"',
            },
        )
        items = data.get("items", []) if isinstance(data, dict) else []
        findings: list[Finding] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            link = str(item.get("link", ""))
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.LOW,
                    kind="paste",
                    value=link,
                    normalized_data={"title": item.get("title")},
                    raw_evidence=Evidence(source_url=link or _BASE),
                    graph_node_hint=GraphNodeHint(
                        node_type="paste",
                        node_id=link,
                        label=str(item.get("title", link))[:80],
                        parent_id=target.value,
                    ),
                )
            )
        return findings
