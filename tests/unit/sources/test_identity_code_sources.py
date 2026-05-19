"""Phase 4 identity & code sources (HTTP mocked, sanitized fixtures)."""

from __future__ import annotations

import hashlib
import json

import httpx

from globeye.core.target import detect
from globeye.sources.code.github import GitHubSource
from globeye.sources.code.pastebin import PastebinSource
from globeye.sources.identity.dehashed import DehashedSource
from globeye.sources.identity.gravatar import GravatarSource
from globeye.sources.identity.hibp import HibpSource
from globeye.sources.identity.hunter import HunterSource


async def test_hibp_breaches(ctx_factory, load_fixture, respx_mock):
    ctx = ctx_factory(hibp_api_key="HIBP-KEY")
    respx_mock.get("https://haveibeenpwned.com/api/v3/breachedaccount/jane@example.com").mock(
        return_value=httpx.Response(200, json=load_fixture("hibp_breaches.json"))
    )
    src = HibpSource(ctx)
    findings = await src.fetch(detect("jane@example.com"))
    await src.aclose()
    assert {f.value for f in findings} == {"ExampleBreach", "AnotherLeak"}
    assert ctx.recorder.hosts == {"haveibeenpwned.com"}


async def test_hibp_not_pwned_is_empty(ctx_factory, respx_mock):
    ctx = ctx_factory(hibp_api_key="HIBP-KEY")
    respx_mock.get("https://haveibeenpwned.com/api/v3/breachedaccount/jane@example.com").mock(
        return_value=httpx.Response(404)
    )
    src = HibpSource(ctx)
    assert await src.fetch(detect("jane@example.com")) == []
    await src.aclose()


async def test_hibp_requires_key(ctx):
    src = HibpSource(ctx)
    assert src.available() is False
    await src.aclose()


async def test_hunter_domain(ctx_factory, load_fixture, respx_mock):
    ctx = ctx_factory(hunter_api_key="HUNTER-KEY")
    respx_mock.get("https://api.hunter.io/v2/domain-search").mock(
        return_value=httpx.Response(200, json=load_fixture("hunter_domain.json"))
    )
    src = HunterSource(ctx)
    findings = await src.fetch(detect("example.com"))
    await src.aclose()
    kinds = {f.kind for f in findings}
    assert "email_pattern" in kinds
    emails = [f for f in findings if f.kind == "email"]
    assert any(f.pivot_target and f.pivot_target.value == "jane.doe@example.com" for f in emails)


async def test_dehashed_drops_credentials(ctx_factory, load_fixture, respx_mock):
    ctx = ctx_factory(dehashed_email="me@example.org", dehashed_api_key="DH-KEY")
    respx_mock.get("https://api.dehashed.com/search").mock(
        return_value=httpx.Response(200, json=load_fixture("dehashed_search.json"))
    )
    src = DehashedSource(ctx)
    findings = await src.fetch(detect("jane.doe@example.com"))
    await src.aclose()
    assert findings[0].value == "ExampleDB"
    blob = json.dumps([f.model_dump(mode="json") for f in findings])
    assert "SHOULD-NOT-BE-STORED" not in blob  # opsec: no credential values
    assert "password" not in findings[0].normalized_data["fields_present"]


async def test_gravatar_profile(ctx, load_fixture, respx_mock):
    digest = hashlib.md5(b"jane.doe@example.com", usedforsecurity=False).hexdigest()
    respx_mock.get(f"https://gravatar.com/{digest}.json").mock(
        return_value=httpx.Response(200, json=load_fixture("gravatar_profile.json"))
    )
    src = GravatarSource(ctx)
    findings = await src.fetch(detect("jane.doe@example.com"))
    await src.aclose()
    usernames = [f for f in findings if f.kind == "username"]
    assert usernames
    assert usernames[0].value == "janedoe"
    assert usernames[0].pivot_target is not None


async def test_github_code(ctx_factory, load_fixture, respx_mock):
    ctx = ctx_factory(github_token="ghp_unit_test_token_value_000000000000")
    respx_mock.get("https://api.github.com/search/code").mock(
        return_value=httpx.Response(200, json=load_fixture("github_code.json"))
    )
    src = GitHubSource(ctx)
    findings = await src.fetch(detect("example.com"))
    await src.aclose()
    assert {f.normalized_data["repository"] for f in findings} == {"acme/app", "acme/infra"}
    assert ctx.recorder.hosts == {"api.github.com"}


async def test_pastebin_via_cse(ctx_factory, load_fixture, respx_mock):
    ctx = ctx_factory(google_cse_key="CSE-KEY", google_cse_cx="CX-ID")
    respx_mock.get("https://www.googleapis.com/customsearch/v1").mock(
        return_value=httpx.Response(200, json=load_fixture("google_cse_pastebin.json"))
    )
    src = PastebinSource(ctx)
    findings = await src.fetch(detect("example.com"))
    await src.aclose()
    assert all(f.value.startswith("https://pastebin.com/") for f in findings)
    assert len(findings) == 2
