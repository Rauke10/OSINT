"""GreyNoise Community source (HTTP mocked)."""

from __future__ import annotations

import httpx

from globeye.core.target import detect
from globeye.sources.infra.greynoise import GreyNoiseSource


async def test_greynoise_requires_key(ctx):
    assert GreyNoiseSource(ctx).available() is False


async def test_greynoise_classification(ctx_factory, load_fixture, respx_mock):
    ctx = ctx_factory(greynoise_api_key="GN-KEY")
    respx_mock.get("https://api.greynoise.io/v3/community/192.0.2.10").mock(
        return_value=httpx.Response(200, json=load_fixture("greynoise_community.json"))
    )
    src = GreyNoiseSource(ctx)
    findings = await src.fetch(detect("192.0.2.10"))
    await src.aclose()
    assert len(findings) == 1
    assert findings[0].kind == "reputation"
    assert findings[0].normalized_data["classification"] == "malicious"
    assert ctx.recorder.hosts == {"api.greynoise.io"}
