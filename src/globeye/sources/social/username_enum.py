"""Passive public-profile presence check.

For a username we issue **one deterministic GET** per platform to that
platform's *public* profile/API endpoint. This is passive by our policy:

* the platforms are third parties, never the target;
* exactly one request per platform — no brute force, no wordlists;
* read-only — we never authenticate, register or submit any form.

See ``SECURITY.md`` for why form-submitting username checkers are banned.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class _Platform:
    name: str
    host: str
    url: str  # contains ``{u}``
    mode: str  # "status" | "truthy" | "keybase"


_PLATFORMS: tuple[_Platform, ...] = (
    _Platform("github", "github.com", "https://github.com/{u}", "status"),
    _Platform("gitlab", "gitlab.com", "https://gitlab.com/{u}", "status"),
    _Platform(
        "reddit",
        "www.reddit.com",
        "https://www.reddit.com/user/{u}/about.json",
        "status",
    ),
    _Platform("devto", "dev.to", "https://dev.to/api/users/by_username?url={u}", "status"),
    _Platform(
        "hackernews",
        "hacker-news.firebaseio.com",
        "https://hacker-news.firebaseio.com/v0/user/{u}.json",
        "truthy",
    ),
    _Platform(
        "keybase",
        "keybase.io",
        "https://keybase.io/_/api/1.0/user/lookup.json?usernames={u}",
        "keybase",
    ),
)


@register
class UsernameEnumSource(PassiveSource):
    """Read-only public-profile presence across well-known platforms."""

    name: ClassVar[str] = "username_enum"
    requires_api_key: ClassVar[bool] = False
    supported_target_types: ClassVar[set[TargetType]] = {TargetType.USERNAME}
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=5, per=1, concurrency=4)
    allowed_hosts: ClassVar[set[str]] = {p.host for p in _PLATFORMS}

    async def _present(self, platform: _Platform, username: str) -> bool:
        url = platform.url.format(u=username)
        if platform.mode == "status":
            text: Any = await self.get_json(url, expect_json=False)
            return text is not None
        data: Any = await self.get_json(url)
        if data is None:
            return False
        if platform.mode == "keybase":
            return bool(data.get("them")) if isinstance(data, dict) else False
        return bool(data)  # "truthy": e.g. HN returns null for missing users

    async def fetch(self, target: Target) -> list[Finding]:
        username = target.value

        async def _one(p: _Platform) -> _Platform | None:
            try:
                return p if await self._present(p, username) else None
            except RuntimeError:
                return None

        results = await asyncio.gather(*(_one(p) for p in _PLATFORMS))
        findings: list[Finding] = []
        for p in results:
            if p is None:
                continue
            url = p.url.format(u=username)
            findings.append(
                Finding(
                    source=self.name,
                    target=username,
                    confidence=Confidence.MEDIUM,
                    kind="social_profile",
                    value=f"{p.name}:{url}",
                    normalized_data={"platform": p.name, "url": url},
                    raw_evidence=Evidence(source_url=url),
                    graph_node_hint=GraphNodeHint(
                        node_type="profile",
                        node_id=url,
                        label=f"{p.name}/{username}",
                        parent_id=username,
                    ),
                )
            )
        return findings
