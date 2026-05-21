"""urlscan.io source (HTTP mocked)."""

from __future__ import annotations

import httpx

from globeye.core.target import detect
from globeye.sources.infra.urlscan import UrlscanSource


async def test_urlscan_search(ctx, load_fixture, respx_mock):
    respx_mock.get("https://urlscan.io/api/v1/search/").mock(
        return_value=httpx.Response(200, json=load_fixture("urlscan_search.json"))
    )
    src = UrlscanSource(ctx)
    findings = await src.fetch(detect("example.com"))
    await src.aclose()
    values = {f.value for f in findings}
    assert values == {"https://example.com/", "https://example.com/login"}
    assert all(f.kind == "archived_url" for f in findings)
    assert ctx.recorder.hosts == {"urlscan.io"}


async def test_urlscan_runs_without_a_key(ctx):
    assert UrlscanSource(ctx).available() is True
