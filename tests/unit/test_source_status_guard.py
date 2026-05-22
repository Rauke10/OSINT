"""Per-source isolation and RDAP Passive Guard allowlist for status probes."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import httpx
from respx import MockRouter

from globeye.config import Settings
from globeye.services.source_credential_probe import (
    DEDICATED_CREDENTIAL_PROBES,
    guard_blocked_probe_result,
    probe_rdap,
)
from globeye.services.source_status import _row_base, _row_probe_failure, describe_source_status
from globeye.sources.infra.virustotal import VirusTotalSource
from globeye.utils.http import DisallowedHostError
from tests.support.settings_env import probe_settings


def _mock_all_keyless_probes(respx_mock: MockRouter, load_fixture: Callable[[str], Any]) -> None:
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


def test_row_probe_failure_disallowed_host():
    row = _row_base(VirusTotalSource, Settings(_env_file=None))
    exc = DisallowedHostError(
        "PASSIVE GUARD: blocked request to non-allowlisted host 'evil.example'"
    )
    out = _row_probe_failure(row, exc, endpoint="test_probe")
    assert out["credential_status"] == "blocked_by_passive_guard"


def test_row_probe_failure_generic_exception():
    row = _row_base(VirusTotalSource, Settings(_env_file=None, virustotal_api_key="x"))
    out = _row_probe_failure(row, ValueError("probe failed"), endpoint="virustotal_probe")
    assert out["credential_status"] == "unknown"
    assert out["checked_endpoint_name"] == "virustotal_probe"


async def test_rdap_probe_follows_redirect_to_verisign(respx_mock):
    settings = Settings(_env_file=None, cache_enabled=False, http_max_retries=0)
    respx_mock.get("https://rdap.org/domain/example.com").mock(
        return_value=httpx.Response(
            302,
            headers={"Location": "https://rdap.verisign.com/domain/example.com"},
        )
    )
    respx_mock.get("https://rdap.verisign.com/domain/example.com").mock(
        return_value=httpx.Response(200, json={"ldhName": "example.com", "entities": []})
    )
    result = await probe_rdap(settings)
    assert result.credential_status == "valid"
    assert result.http_status == 200
    assert "rdap.verisign.com" in str(respx_mock.calls[-1].request.url)


async def test_guard_blocked_probe_result_message():
    exc = DisallowedHostError(
        "PASSIVE GUARD: blocked request to non-allowlisted host 'rdap.verisign.com'"
    )
    result = guard_blocked_probe_result(exc, endpoint_name="rdap_domain")
    assert result.credential_status == "blocked_by_passive_guard"
    assert result.http_status is None
    assert "rdap.verisign.com" in (result.provider_error_message_sanitized or "")


async def test_describe_status_isolates_connect_error(load_fixture, respx_mock, monkeypatch):
    settings = probe_settings(monkeypatch, virustotal="VT-OK")
    respx_mock.routes.clear()
    _mock_all_keyless_probes(respx_mock, load_fixture)

    async def _fail_vt(_settings: Settings):
        raise httpx.ConnectError("connection refused")

    probes = dict(DEDICATED_CREDENTIAL_PROBES)
    probes["virustotal"] = _fail_vt
    with patch.dict(DEDICATED_CREDENTIAL_PROBES, probes, clear=False):
        rows = await describe_source_status(settings, probe=True)

    vt = next(r for r in rows if r["name"] == "virustotal")
    assert vt["credential_status"] == "network_error"
    assert next(r for r in rows if r["name"] == "crtsh")["credential_status"] in {
        "valid",
        "keyless",
    }


async def test_describe_status_isolates_guard_error(load_fixture, respx_mock, monkeypatch):
    settings = probe_settings(monkeypatch, virustotal="VT-OK")
    respx_mock.routes.clear()
    _mock_all_keyless_probes(respx_mock, load_fixture)

    async def _blocked_rdap(_settings: Settings):
        raise DisallowedHostError(
            "PASSIVE GUARD: blocked request to non-allowlisted host 'rdap.verisign.com'"
        )

    respx_mock.get("https://www.virustotal.com/api/v3/domains/example.com").mock(
        return_value=httpx.Response(200, json={"data": {"attributes": {}}})
    )

    probes = dict(DEDICATED_CREDENTIAL_PROBES)
    probes["rdap"] = _blocked_rdap
    with patch.dict(DEDICATED_CREDENTIAL_PROBES, probes, clear=False):
        rows = await describe_source_status(settings, probe=True)

    rdap = next(r for r in rows if r["name"] == "rdap")
    vt = next(r for r in rows if r["name"] == "virustotal")
    assert rdap["credential_status"] == "blocked_by_passive_guard"
    assert vt["credential_status"] == "valid"
    assert vt["http_status"] == 200
