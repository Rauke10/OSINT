"""ThreatFox (abuse.ch) source (HTTP mocked)."""

from __future__ import annotations

import httpx

from globeye.core.target import detect
from globeye.sources.intel.threatfox import ThreatFoxSource


async def test_threatfox_iocs(ctx, load_fixture, respx_mock):
    respx_mock.post("https://threatfox-api.abuse.ch/api/v1/").mock(
        return_value=httpx.Response(200, json=load_fixture("threatfox_search.json"))
    )
    src = ThreatFoxSource(ctx)
    findings = await src.fetch(detect("example.com"))
    await src.aclose()
    assert len(findings) == 1
    assert findings[0].kind == "ioc"
    assert findings[0].normalized_data["malware"] == "ExampleBot"
    assert ctx.recorder.hosts == {"threatfox-api.abuse.ch"}
