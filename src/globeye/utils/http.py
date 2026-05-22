"""Async HTTP client with the passive-only guard, retries and proxy support.

Every source is given a client scoped to *its* allowlisted third-party hosts.
A request event hook blocks any request whose host is not on that allowlist —
this is what makes "never contact the target" a hard, testable invariant
(the target host is never on any allowlist).
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from globeye.config import Settings
from globeye.utils.cache import DiskCache

_RETRY_STATUS = {429, 500, 502, 503, 504}


class DisallowedHostError(RuntimeError):
    """Raised when code tries to reach a host outside the allowlist."""


class RequestRecorder:
    """Records every outbound URL (used by the no-target-traffic test)."""

    def __init__(self) -> None:
        self.urls: list[str] = []

    @property
    def hosts(self) -> set[str]:
        return {httpx.URL(u).host for u in self.urls}


def build_client(
    settings: Settings,
    allowed_hosts: set[str],
    *,
    recorder: RequestRecorder | None = None,
) -> httpx.AsyncClient:
    """Build an :class:`httpx.AsyncClient` locked to ``allowed_hosts``."""
    allowed = {h.lower().lstrip(".") for h in allowed_hosts}

    async def _guard(request: httpx.Request) -> None:
        host = (request.url.host or "").lower()
        if recorder is not None:
            recorder.urls.append(str(request.url))
        ok = host in allowed or any(host == a or host.endswith("." + a) for a in allowed)
        if not ok:
            raise DisallowedHostError(
                f"PASSIVE GUARD: blocked request to non-allowlisted host {host!r}"
            )

    return httpx.AsyncClient(
        timeout=settings.http_timeout_seconds,
        headers={"User-Agent": settings.user_agent, "Accept-Encoding": "gzip"},
        proxy=settings.proxy_url or None,
        follow_redirects=True,
        event_hooks={"request": [_guard]},
    )


async def request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    settings: Settings,
    cache: DiskCache | None = None,
    cache_namespace: str = "http",
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    json_body: Any | None = None,
    expect_json: bool = True,
) -> Any:
    """HTTP request with disk cache + exponential-backoff retries.

    Returns parsed JSON (``expect_json=True``) or the response text.
    ``None`` is returned for 404 (treated as "no data", not an error).
    """
    cache_key = f"{method}:{url}:{sorted((params or {}).items())}"
    if cache is not None:
        hit = cache.get(cache_namespace, cache_key)
        if hit is not None:
            return hit

    last_exc: Exception | None = None
    for attempt in range(settings.http_max_retries + 1):
        try:
            resp = await client.request(method, url, params=params, headers=headers, json=json_body)
            if resp.status_code == 404:
                return None
            if resp.status_code in _RETRY_STATUS:
                raise httpx.HTTPStatusError(
                    f"retryable status {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            resp.raise_for_status()
            if expect_json:
                try:
                    data = resp.json()
                except ValueError as exc:
                    raise RuntimeError(f"invalid JSON from {url}: {exc}") from exc
            else:
                data = resp.text
            if cache is not None:
                cache.set(cache_namespace, cache_key, data)
            return data
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_exc = exc
            if attempt >= settings.http_max_retries:
                break
            await asyncio.sleep(2.0**attempt)

    raise RuntimeError(f"request to {url} failed after retries: {last_exc}") from last_exc
