"""HTTP layer: passive guard + retry/cache behaviour."""

from __future__ import annotations

import httpx
import pytest

from globeye.utils.http import (
    DisallowedHostError,
    RequestRecorder,
    build_client,
    request_json,
)


async def test_guard_blocks_non_allowlisted_host(settings):
    rec = RequestRecorder()
    client = build_client(settings, {"crt.sh"}, recorder=rec)
    with pytest.raises(DisallowedHostError):
        await client.get("https://target.example/")
    await client.aclose()
    # Recorded for the audit test, but the request was never actually sent.
    assert rec.hosts == {"target.example"}


async def test_guard_allows_allowlisted_host(settings, respx_mock):
    respx_mock.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=[]))
    client = build_client(settings, {"crt.sh"})
    resp = await client.get("https://crt.sh/")
    await client.aclose()
    assert resp.status_code == 200


async def test_request_json_retries_then_succeeds(settings, respx_mock):
    route = respx_mock.get("https://crt.sh/")
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(200, json={"ok": True}),
    ]
    client = build_client(settings, {"crt.sh"})
    data = await request_json(client, "GET", "https://crt.sh/", settings=settings, cache=None)
    await client.aclose()
    assert data == {"ok": True}
    assert route.call_count == 2


async def test_request_json_404_is_none(settings, respx_mock):
    respx_mock.get("https://crt.sh/").mock(return_value=httpx.Response(404))
    client = build_client(settings, {"crt.sh"})
    assert await request_json(client, "GET", "https://crt.sh/", settings=settings) is None
    await client.aclose()


async def test_request_json_uses_cache(settings, respx_mock, ctx):
    route = respx_mock.get("https://crt.sh/").mock(return_value=httpx.Response(200, json={"v": 1}))
    client = build_client(settings, {"crt.sh"})
    a = await request_json(client, "GET", "https://crt.sh/", settings=settings, cache=ctx.cache)
    b = await request_json(client, "GET", "https://crt.sh/", settings=settings, cache=ctx.cache)
    await client.aclose()
    assert a == b == {"v": 1}
    assert route.call_count == 1  # second call served from disk cache
