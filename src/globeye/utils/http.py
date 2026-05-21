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

# Query-string parameters that must never reach the disk cache key — some
# APIs (Shodan, Hunter, Google CSE) only accept their key as a query param.
SENSITIVE_PARAM_KEYS = frozenset(
    {"api_key", "apikey", "key", "token", "access_token", "auth", "secret"}
)


def cache_key_for(method: str, url: str, params: dict[str, Any] | None) -> str:
    """Build a disk-cache key with secret query parameters stripped out."""
    safe = sorted(
        (k, v) for k, v in (params or {}).items() if k.lower() not in SENSITIVE_PARAM_KEYS
    )
    return f"{method}:{url}:{safe}"


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
        proxy=settings.proxy_url,
        follow_redirects=True,
        event_hooks={"request": [_guard]},
    )


def _summarize(exc: Exception | None) -> str:
    """Turn a low-level HTTP exception into a short, human reason."""
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403):
            return f"HTTP {code} (blocked — the source rejected the request)"
        if code == 429:
            return "HTTP 429 (rate-limited by the source)"
        return f"HTTP {code}"
    if isinstance(exc, httpx.TimeoutException):
        return "timeout (source did not respond)"
    if isinstance(exc, httpx.TransportError):
        return "network error (source unreachable)"
    return str(exc) if exc else "request failed"


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
    On failure raises ``RuntimeError`` with a short, human-readable reason.
    Only 429/5xx are retried; other 4xx (401/403/...) fail fast.
    """
    cache_key = cache_key_for(method, url, params)
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
            resp.raise_for_status()
            if expect_json:
                try:
                    data = resp.json()
                except ValueError as exc:
                    raise RuntimeError(f"invalid JSON from {url}") from exc
            else:
                data = resp.text
            if cache is not None:
                cache.set(cache_namespace, cache_key, data)
            return data
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            retryable = exc.response.status_code in _RETRY_STATUS
            if not retryable or attempt >= settings.http_max_retries:
                break
            await asyncio.sleep(2.0**attempt)
        except httpx.TransportError as exc:
            last_exc = exc
            if attempt >= settings.http_max_retries:
                break
            await asyncio.sleep(2.0**attempt)

    raise RuntimeError(_summarize(last_exc)) from last_exc
