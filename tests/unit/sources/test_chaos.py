"""Chaos (ProjectDiscovery) source (HTTP mocked)."""

from __future__ import annotations

import httpx

from globeye.core.target import detect
from globeye.sources.infra.chaos import ChaosSource


async def test_chaos_requires_key(ctx):
    assert ChaosSource(ctx).available() is False


async def test_chaos_subdomains(ctx_factory, load_fixture, respx_mock):
    ctx = ctx_factory(chaos_api_key="CHAOS-KEY")
    respx_mock.get("https://chaos.projectdiscovery.io/api/v1/example.com/subdomains").mock(
        return_value=httpx.Response(200, json=load_fixture("chaos_subdomains.json"))
    )
    src = ChaosSource(ctx)
    findings = await src.fetch(detect("example.com"))
    await src.aclose()
    assert {f.value for f in findings} == {
        "www.example.com",
        "api.example.com",
        "vpn.example.com",
    }
    assert ctx.recorder.hosts == {"chaos.projectdiscovery.io"}
