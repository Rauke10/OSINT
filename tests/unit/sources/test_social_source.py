"""Phase 5 social source: passive public-profile presence (HTTP mocked)."""

from __future__ import annotations

from typing import Any

import httpx

from globeye.core.target import detect
from globeye.sources.social.username_enum import UsernameEnumSource


def _mock_all(
    respx_mock: Any,
    *,
    github: bool,
    gitlab: bool,
    reddit: bool,
    devto: bool,
    hn: bool,
    keybase: bool,
) -> None:
    respx_mock.get("https://github.com/octocat").mock(
        return_value=httpx.Response(200 if github else 404, text="ok")
    )
    respx_mock.get("https://gitlab.com/octocat").mock(
        return_value=httpx.Response(200 if gitlab else 404, text="ok")
    )
    respx_mock.get("https://www.reddit.com/user/octocat/about.json").mock(
        return_value=httpx.Response(200 if reddit else 404, json={"data": {}})
    )
    respx_mock.get("https://dev.to/api/users/by_username").mock(
        return_value=httpx.Response(200 if devto else 404, json={})
    )
    respx_mock.get("https://hacker-news.firebaseio.com/v0/user/octocat.json").mock(
        return_value=httpx.Response(
            200,
            content=b'{"id": "octocat"}' if hn else b"null",
            headers={"content-type": "application/json"},
        )
    )
    respx_mock.get("https://keybase.io/_/api/1.0/user/lookup.json").mock(
        return_value=httpx.Response(
            200, json={"status": {"code": 0}, "them": [{"id": "x"}] if keybase else []}
        )
    )


async def test_username_presence(ctx, respx_mock):
    _mock_all(
        respx_mock,
        github=True,
        gitlab=False,
        reddit=True,
        devto=False,
        hn=False,
        keybase=True,
    )
    src = UsernameEnumSource(ctx)
    findings = await src.fetch(detect("octocat"))
    await src.aclose()

    platforms = {f.normalized_data["platform"] for f in findings}
    assert platforms == {"github", "reddit", "keybase"}
    assert all(f.kind == "social_profile" for f in findings)
    assert ctx.recorder.hosts <= UsernameEnumSource.allowed_hosts


async def test_username_absent_everywhere(ctx, respx_mock):
    _mock_all(
        respx_mock,
        github=False,
        gitlab=False,
        reddit=False,
        devto=False,
        hn=False,
        keybase=False,
    )
    src = UsernameEnumSource(ctx)
    assert await src.fetch(detect("octocat")) == []
    await src.aclose()
