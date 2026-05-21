"""Cache keys must never contain secret query parameters."""

from __future__ import annotations

import httpx

from globeye.utils.http import (
    SENSITIVE_PARAM_KEYS,
    RequestSpec,
    build_client,
    cache_key_for,
    request,
)


def test_cache_key_strips_sensitive_params():
    a = cache_key_for("GET", "https://api.example/", {"key": "AAA", "q": "x"})
    b = cache_key_for("GET", "https://api.example/", {"key": "BBB", "q": "x"})
    assert a == b
    assert "AAA" not in a
    assert "BBB" not in b
    assert "q" in a  # non-secret params are still part of the key


def test_every_sensitive_key_is_stripped():
    for k in SENSITIVE_PARAM_KEYS:
        key = cache_key_for("GET", "https://x/", {k: "SECRET", k.upper(): "SECRET"})
        assert "SECRET" not in key


async def test_request_cache_ignores_api_key(settings, respx_mock, ctx):
    route = respx_mock.get("https://api.shodan.io/x").mock(
        return_value=httpx.Response(200, json={"v": 1})
    )
    client = build_client(settings, {"api.shodan.io"})
    a = await request(
        client,
        RequestSpec(url="https://api.shodan.io/x", params={"key": "KEY-1"}),
        settings=settings,
        cache=ctx.cache,
    )
    # A different API key on the same URL must hit the cache, not the network.
    b = await request(
        client,
        RequestSpec(url="https://api.shodan.io/x", params={"key": "KEY-2"}),
        settings=settings,
        cache=ctx.cache,
    )
    await client.aclose()
    assert a == b == {"v": 1}
    assert route.call_count == 1
