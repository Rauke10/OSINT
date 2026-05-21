"""EmailRep source (HTTP mocked)."""

from __future__ import annotations

import httpx

from globeye.core.target import detect
from globeye.sources.identity.emailrep import EmailRepSource


async def test_emailrep_reputation(ctx, load_fixture, respx_mock):
    respx_mock.get("https://emailrep.io/jane@example.com").mock(
        return_value=httpx.Response(200, json=load_fixture("emailrep.json"))
    )
    src = EmailRepSource(ctx)
    findings = await src.fetch(detect("jane@example.com"))
    await src.aclose()
    assert len(findings) == 1
    assert findings[0].kind == "email_reputation"
    # A suspicious address is reported with high confidence.
    assert findings[0].confidence.value == "high"
    assert ctx.recorder.hosts == {"emailrep.io"}
