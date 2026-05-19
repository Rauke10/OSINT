"""GitHub code search — public code that references the target (passive).

We query GitHub's search index (a third party). We never touch the target.
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

_BASE = "https://api.github.com"


@register
class GitHubSource(PassiveSource):
    """GitHub code-search lookup for leaked references."""

    name: ClassVar[str] = "github"
    requires_api_key: ClassVar[bool] = True
    supported_target_types: ClassVar[set[TargetType]] = {
        TargetType.DOMAIN,
        TargetType.EMAIL,
        TargetType.ORG,
    }
    # Authenticated code-search limit is ~10 requests/minute.
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=10, per=60, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"api.github.com"}

    def api_key(self) -> str | None:
        token = self.ctx.settings.github_token
        return token.get_secret_value() if token else None

    async def fetch(self, target: Target) -> list[Finding]:
        token = self.api_key()
        if not token:
            return []
        data: Any = await self.get_json(
            f"{_BASE}/search/code",
            params={"q": f'"{target.value}"', "per_page": "30"},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
        items = data.get("items", []) if isinstance(data, dict) else []
        findings: list[Finding] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            repo = item.get("repository", {}) or {}
            full = str(repo.get("full_name", "?"))
            path = str(item.get("path", "?"))
            html_url = str(item.get("html_url", ""))
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.LOW,
                    kind="code_reference",
                    value=f"{full}/{path}",
                    normalized_data={"repository": full, "path": path},
                    raw_evidence=Evidence(source_url=html_url or f"{_BASE}/search/code"),
                    graph_node_hint=GraphNodeHint(
                        node_type="repo",
                        node_id=full,
                        label=full,
                        parent_id=target.value,
                    ),
                )
            )
        return findings
