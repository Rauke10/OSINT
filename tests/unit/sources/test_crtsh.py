"""crt.sh source: parsing + the passive (no-target-traffic) invariant."""

from __future__ import annotations

import httpx

from globeye.core.target import detect
from globeye.sources.infra.crtsh import CrtShSource


async def test_crtsh_parses_subdomains(ctx, load_fixture, respx_mock):
    respx_mock.get("https://crt.sh/").mock(
        return_value=httpx.Response(200, json=load_fixture("crtsh_example_com.json"))
    )
    src = CrtShSource(ctx)
    findings = await src.fetch(detect("example.com"))
    await src.aclose()

    values = {f.value for f in findings}
    assert {"example.com", "api.example.com", "www.example.com", "mail.example.com"} <= values
    assert "other.test" not in values  # not under the target apex
    assert "admin@example.com" not in values  # emails are not subdomains
    assert all(f.source == "crtsh" and f.confidence.value == "high" for f in findings)
    assert findings[0].graph_node_hint is not None


async def test_crtsh_handles_no_data(ctx, respx_mock):
    respx_mock.get("https://crt.sh/").mock(return_value=httpx.Response(200, json={}))
    src = CrtShSource(ctx)
    assert await src.fetch(detect("example.com")) == []
    await src.aclose()


async def test_crtsh_never_contacts_target(ctx, load_fixture, respx_mock):
    respx_mock.get("https://crt.sh/").mock(
        return_value=httpx.Response(200, json=load_fixture("crtsh_example_com.json"))
    )
    src = CrtShSource(ctx)
    await src.fetch(detect("example.com"))
    await src.aclose()

    # The hard invariant: only the allowlisted third party was contacted.
    assert ctx.recorder.hosts == {"crt.sh"}
    assert all(httpx.URL(u).host == "crt.sh" for u in ctx.recorder.urls)
