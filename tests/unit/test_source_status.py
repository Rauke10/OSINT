"""Source configuration and status checks."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

import httpx
from respx import MockRouter

from globeye.config import Settings
from globeye.services.source_credentials import is_configured
from globeye.services.source_status import describe_source_status
from tests.support.settings_env import build_settings


def test_is_configured_shodan(monkeypatch):
    empty = Settings(_env_file=None)
    assert is_configured(empty, "shodan", requires_api_key=True) is False
    filled = build_settings(monkeypatch, shodan="KEY-123")
    assert is_configured(filled, "shodan", requires_api_key=True) is True


def test_is_configured_keyless_crtsh():
    s = Settings(_env_file=None)
    assert is_configured(s, "crtsh", requires_api_key=False) is True


def test_censys_requires_both_parts(monkeypatch):
    s = build_settings(monkeypatch, censys_id="ID")
    assert is_configured(s, "censys", requires_api_key=True) is False
    s2 = build_settings(monkeypatch, censys_id="ID", censys_pass="SECRET")
    assert is_configured(s2, "censys", requires_api_key=True) is True


async def test_describe_censys_incompatible_without_http(load_fixture, respx_mock, monkeypatch):
    settings = build_settings(
        monkeypatch,
        censys_id="censys_only_id_part",
        censys_pass="censys-test-val",
    )
    respx_mock.routes.clear()
    _mock_keyless_probes(respx_mock, load_fixture)
    rows = await describe_source_status(settings, probe=True)
    censys = next(r for r in rows if r["name"] == "censys")
    assert censys["credential_status"] == "incompatible_credentials"
    assert censys["probe_scan_status"] == "skipped"


async def test_describe_configured_not_checked(settings, monkeypatch):
    settings = build_settings(monkeypatch, virustotal="VT-TEST")
    rows = await describe_source_status(settings, probe=False)
    vt = next(r for r in rows if r["name"] == "virustotal")
    assert vt["credential_status"] == "configured_not_checked"
    assert vt["configured"] is True


async def test_describe_without_probe(settings):
    rows = await describe_source_status(settings, probe=False)
    by_name = {r["name"]: r for r in rows}
    assert by_name["crtsh"]["credential_status"] == "keyless"
    assert by_name["shodan"]["credential_status"] == "missing_key"
    assert by_name["shodan"]["status"] == "missing_key"


def _mock_keyless_probes(respx_mock: MockRouter, load_fixture: Callable[[str], Any]) -> None:
    respx_mock.get("https://crt.sh/").mock(
        return_value=httpx.Response(200, json=load_fixture("crtsh_example_com.json"))
    )
    respx_mock.get("https://web.archive.org/cdx/search/cdx").mock(
        return_value=httpx.Response(200, json=[["urlkey"], ["http://example.com/"]])
    )
    respx_mock.get("https://rdap.org/domain/example.com").mock(
        return_value=httpx.Response(200, json={"ldhName": "example.com", "entities": []})
    )
    digest = hashlib.md5(b"test@example.com", usedforsecurity=False).hexdigest()
    respx_mock.get(f"https://gravatar.com/{digest}.json").mock(return_value=httpx.Response(404))
    for url in (
        "https://github.com/example",
        "https://gitlab.com/example",
        "https://www.reddit.com/user/example/about.json",
        "https://dev.to/api/users/by_username?url=example",
        "https://hacker-news.firebaseio.com/v0/user/example.json",
        "https://keybase.io/_/api/1.0/user/lookup.json?usernames=example",
    ):
        respx_mock.get(url).mock(return_value=httpx.Response(404))


async def test_describe_probe_shodan_ok(ctx_factory, load_fixture, respx_mock, monkeypatch):
    settings = build_settings(monkeypatch, shodan="UNIT-TEST-KEY")
    respx_mock.routes.clear()
    _mock_keyless_probes(respx_mock, load_fixture)
    respx_mock.get(url__regex=r"https://api\.shodan\.io/dns/domain/example\.com").mock(
        return_value=httpx.Response(200, json=load_fixture("shodan_dns_example_com.json"))
    )
    rows = await describe_source_status(settings, probe=True)
    shodan = next(r for r in rows if r["name"] == "shodan")
    assert shodan["status"] == "ok"
    assert shodan["credential_status"] == "valid"
    assert shodan["http_status"] == 200
    assert shodan["checked_endpoint_name"] == "shodan_dns_domain"
    assert shodan["configured"] is True


async def test_describe_probe_abuseipdb_invalid(load_fixture, respx_mock, monkeypatch):
    settings = build_settings(monkeypatch, abuseipdb="BAD-KEY")
    respx_mock.routes.clear()
    _mock_keyless_probes(respx_mock, load_fixture)
    respx_mock.get("https://api.abuseipdb.com/api/v2/check").mock(
        return_value=httpx.Response(401, json={"errors": [{"detail": "Unauthorized"}]})
    )
    rows = await describe_source_status(settings, probe=True)
    abuse = next(r for r in rows if r["name"] == "abuseipdb")
    assert abuse["credential_status"] == "invalid_key"
    assert abuse["http_status"] == 401
    assert abuse["auth_method"] == "Key header"


async def test_describe_probe_invalid_key(ctx_factory, load_fixture, respx_mock, monkeypatch):
    settings = build_settings(monkeypatch, shodan="BAD")
    respx_mock.routes.clear()
    _mock_keyless_probes(respx_mock, load_fixture)
    respx_mock.get(url__regex=r"https://api\.shodan\.io/dns/domain/example\.com").mock(
        return_value=httpx.Response(401, json={"error": "Invalid API key"})
    )
    rows = await describe_source_status(settings, probe=True)
    shodan = next(r for r in rows if r["name"] == "shodan")
    assert shodan["status"] == "invalid_key"
    assert shodan["credential_status"] == "invalid_key"
    assert shodan["http_status"] == 401
