"""The :class:`PassiveSource` ABC and the source registry.

Every source is a third-party lookup that only ever talks to its own
``allowed_hosts``. Sources self-register with :func:`register`, so adding a
source means adding **one module** — no shared file to edit.
"""

from __future__ import annotations

import importlib
import pkgutil
from abc import ABC, abstractmethod
from typing import Any, ClassVar

import httpx

from globeye.core.context import ScanContext
from globeye.core.models import (
    Finding,
    RateLimit,
    SourceStatus,
    Target,
    TargetType,
)
from globeye.utils.http import JSONValue, RequestSpec, build_client, request
from globeye.utils.ratelimit import AsyncRateLimiter

SOURCE_REGISTRY: list[type[PassiveSource]] = []


def register(cls: type[PassiveSource]) -> type[PassiveSource]:
    """Class decorator that adds a source to the global registry."""
    SOURCE_REGISTRY.append(cls)
    return cls


def discover_sources() -> list[type[PassiveSource]]:
    """Import every ``globeye.sources.*`` submodule so they self-register."""
    import globeye.sources as pkg

    for mod in pkgutil.walk_packages(pkg.__path__, prefix="globeye.sources."):
        if mod.name.endswith(".base"):
            continue
        importlib.import_module(mod.name)
    return SOURCE_REGISTRY


class PassiveSource(ABC):
    """Common interface for all passive sources."""

    name: ClassVar[str]
    requires_api_key: ClassVar[bool] = False
    supported_target_types: ClassVar[set[TargetType]]
    rate_limit: ClassVar[RateLimit] = RateLimit()
    allowed_hosts: ClassVar[set[str]]

    def __init__(self, ctx: ScanContext) -> None:
        self.ctx = ctx
        self._client: httpx.AsyncClient | None = None
        self._limiter = AsyncRateLimiter(self.rate_limit)

    # --- capability checks ---------------------------------------------------
    def applicable(self, target: Target) -> bool:
        return target.type in self.supported_target_types

    def api_key(self) -> str | None:
        """Return this source's API key, if any. Override when needed."""
        return None

    def available(self) -> bool:
        """Whether the source can run (key present when required)."""
        return not self.requires_api_key or bool(self.api_key())

    # --- networking ----------------------------------------------------------
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = build_client(
                self.ctx.settings,
                self.allowed_hosts,
                recorder=self.ctx.recorder,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_json(
        self,
        url: str,
        *,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_body: Any | None = None,
        expect_json: bool = True,
    ) -> JSONValue:
        """Rate-limited, cached, retried request scoped to allowed hosts."""
        spec = RequestSpec(
            method=method,
            url=url,
            params=params,
            headers=headers,
            json_body=json_body,
            cache_namespace=self.name,
            expect_json=expect_json,
        )
        async with self._limiter:
            return await request(
                self.client,
                spec,
                settings=self.ctx.settings,
                cache=self.ctx.cache,
            )

    # --- lifecycle -----------------------------------------------------------
    @abstractmethod
    async def fetch(self, target: Target) -> list[Finding]:
        """Return findings for ``target`` from this third party."""

    async def health_check(self) -> SourceStatus:
        """Passive health check (no target traffic; no probing by default)."""
        return SourceStatus(
            name=self.name,
            available=self.available(),
            requires_api_key=self.requires_api_key,
            has_api_key=bool(self.api_key()),
            detail=None if self.available() else "missing API key",
        )
