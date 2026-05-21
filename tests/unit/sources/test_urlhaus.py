"""URLhaus (abuse.ch) source (HTTP mocked)."""

from __future__ import annotations

import httpx

from globeye.core.target import detect
from globeye.sources.intel.urlhaus import UrlhausSource


async def test_urlhaus_malicious_urls(ctx, load_fixture, respx_mock):
    respx_mock.post("https://urlhaus-api.abuse.ch/v1/host/").mock(
        return_value=httpx.Response(200, json=load_fixture("urlhaus_host.json"))
    )
    src = UrlhausSource(ctx)
    findings = await src.fetch(detect("example.com"))
    await src.aclose()
    assert len(findings) == 1
    assert findings[0].kind == "malicious_url"
    assert findings[0].confidence.value == "high"
    assert ctx.recorder.hosts == {"urlhaus-api.abuse.ch"}


async def test_urlhaus_no_results(ctx, respx_mock):
    respx_mock.post("https://urlhaus-api.abuse.ch/v1/host/").mock(
        return_value=httpx.Response(200, json={"query_status": "no_results"})
    )
    src = UrlhausSource(ctx)
    assert await src.fetch(detect("example.com")) == []
    await src.aclose()
