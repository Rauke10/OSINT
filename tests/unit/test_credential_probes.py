"""Dedicated credential probe HTTP mapping."""

from __future__ import annotations

import base64

import httpx

from globeye.services.source_credential_probe import (
    censys_credential_issue,
    probe_abuseipdb,
    probe_censys,
    probe_crtsh,
    probe_hunter,
    probe_virustotal,
    probe_wayback,
)
from tests.support.settings_env import build_settings, probe_settings


async def test_abuseipdb_200_valid(respx_mock, monkeypatch):
    settings = probe_settings(monkeypatch, abuseipdb="KEY")
    respx_mock.get("https://api.abuseipdb.com/api/v2/check").mock(
        return_value=httpx.Response(200, json={"data": {"abuseConfidenceScore": 0}})
    )
    r = await probe_abuseipdb(settings)
    assert r.credential_status == "valid"
    assert r.http_status == 200
    assert r.auth_method == "Key header"
    assert r.checked_endpoint_name == "abuseipdb_ip_check"


async def test_abuseipdb_401_invalid(respx_mock, monkeypatch):
    settings = probe_settings(monkeypatch, abuseipdb="BAD")
    respx_mock.get("https://api.abuseipdb.com/api/v2/check").mock(
        return_value=httpx.Response(401, json={"errors": [{"detail": "Unauthorized"}]})
    )
    r = await probe_abuseipdb(settings)
    assert r.credential_status == "invalid_key"
    assert r.http_status == 401


async def test_abuseipdb_403_forbidden(respx_mock, monkeypatch):
    settings = probe_settings(monkeypatch, abuseipdb="KEY")
    respx_mock.get("https://api.abuseipdb.com/api/v2/check").mock(
        return_value=httpx.Response(403, json={"errors": [{"detail": "Forbidden"}]})
    )
    r = await probe_abuseipdb(settings)
    assert r.credential_status == "forbidden"
    assert r.http_status == 403


async def test_virustotal_200_and_401(respx_mock, monkeypatch):
    settings = probe_settings(monkeypatch, virustotal="VT-KEY")
    respx_mock.get("https://www.virustotal.com/api/v3/domains/example.com").mock(
        return_value=httpx.Response(200, json={"data": {"attributes": {}}})
    )
    ok = await probe_virustotal(settings)
    assert ok.credential_status == "valid"
    assert ok.auth_method == "x-apikey header"

    respx_mock.get("https://www.virustotal.com/api/v3/domains/example.com").mock(
        return_value=httpx.Response(401, json={"error": {"code": "AuthenticationRequiredError"}})
    )
    bad = await probe_virustotal(settings)
    assert bad.credential_status == "invalid_key"
    assert bad.http_status == 401


async def test_hunter_200_401_403(respx_mock, monkeypatch):
    settings = probe_settings(monkeypatch, hunter="H-KEY")
    respx_mock.get("https://api.hunter.io/v2/domain-search").mock(
        return_value=httpx.Response(200, json={"data": {"emails": []}})
    )
    assert (await probe_hunter(settings)).credential_status == "valid"

    respx_mock.get("https://api.hunter.io/v2/domain-search").mock(
        return_value=httpx.Response(401, json={"errors": [{"id": "auth"}]})
    )
    assert (await probe_hunter(settings)).credential_status == "invalid_key"

    respx_mock.get("https://api.hunter.io/v2/domain-search").mock(
        return_value=httpx.Response(403, json={"errors": [{"id": "forbidden"}]})
    )
    assert (await probe_hunter(settings)).credential_status == "forbidden"


async def test_censys_legacy_200_and_401(respx_mock, monkeypatch):
    settings = probe_settings(monkeypatch, censys_id="UID", censys_pass="SECRET")
    auth = base64.b64encode(b"UID:SECRET").decode()
    respx_mock.get("https://search.censys.io/api/v1/account").mock(
        return_value=httpx.Response(
            200, json={"login": "user@example.com"}, headers={"Authorization": f"Basic {auth}"}
        )
    )
    ok = await probe_censys(settings)
    assert ok.credential_status == "valid"
    assert ok.checked_endpoint_name == "censys_legacy_account"

    respx_mock.get("https://search.censys.io/api/v1/account").mock(
        return_value=httpx.Response(401, json={"error": "Unauthorized"})
    )
    bad = await probe_censys(settings)
    assert bad.credential_status == "invalid_key"


async def test_censys_platform_token_env(monkeypatch):
    settings = probe_settings(monkeypatch, censys_pat="censys_pat_only")
    r = await probe_censys(settings)
    assert r.credential_status == "incompatible_credentials"


async def test_abuseipdb_network_error(respx_mock, monkeypatch):
    settings = probe_settings(monkeypatch, abuseipdb="KEY")
    respx_mock.get("https://api.abuseipdb.com/api/v2/check").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    r = await probe_abuseipdb(settings)
    assert r.credential_status == "network_error"
    assert r.probe_scan_status == "network_error"


async def test_censys_platform_pat_incompatible(monkeypatch):
    settings = build_settings(
        monkeypatch,
        censys_id="censys_abc_part",
        censys_pass="censys-test-val",
    )
    assert censys_credential_issue(settings) is not None
    r = await probe_censys(settings)
    assert r.credential_status == "incompatible_credentials"


async def test_crtsh_timeout_provider_timeout(respx_mock, monkeypatch):
    settings = build_settings(monkeypatch, crtsh_probe_timeout_seconds=0.01)

    def _timeout(_request):
        raise httpx.ReadTimeout("slow")

    respx_mock.get("https://crt.sh/").mock(side_effect=_timeout)
    r = await probe_crtsh(settings)
    assert r.credential_status == "provider_timeout"
    assert r.probe_scan_status == "provider_timeout"


async def test_shodan_probe_200(respx_mock, load_fixture, monkeypatch):
    from globeye.services.source_credential_probe import probe_shodan

    settings = probe_settings(monkeypatch, shodan="KEY")
    respx_mock.get(url__regex=r"https://api\.shodan\.io/dns/domain/example\.com").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    r = await probe_shodan(settings)
    assert r.credential_status == "valid"
    assert r.checked_endpoint_name == "shodan_dns_domain"


async def test_probe_request_guard_blocked_on_wrong_allowlist(monkeypatch):
    from globeye.services.source_credential_probe import _probe_request

    settings = probe_settings(monkeypatch)
    result = await _probe_request(
        settings,
        allowed_hosts={"rdap.org"},
        method="GET",
        url="https://rdap.verisign.com/domain/example.com",
        endpoint_name="rdap_test",
        auth_method="none",
    )
    assert result.credential_status == "blocked_by_passive_guard"


async def test_rdap_probe_200(respx_mock, monkeypatch):
    from globeye.services.source_credential_probe import probe_rdap

    settings = probe_settings(monkeypatch)
    respx_mock.get("https://rdap.org/domain/example.com").mock(
        return_value=httpx.Response(200, json={"entities": []})
    )
    r = await probe_rdap(settings)
    assert r.credential_status == "valid"


async def test_abuseipdb_429_rate_limited(respx_mock, monkeypatch):
    settings = probe_settings(monkeypatch, abuseipdb="KEY")
    respx_mock.get("https://api.abuseipdb.com/api/v2/check").mock(
        return_value=httpx.Response(429, json={"errors": [{"detail": "Too many requests"}]})
    )
    r = await probe_abuseipdb(settings)
    assert r.credential_status == "rate_limited"
    assert r.http_status == 429


async def test_virustotal_403_forbidden(respx_mock, monkeypatch):
    settings = probe_settings(monkeypatch, virustotal="VT")
    respx_mock.get("https://www.virustotal.com/api/v3/domains/example.com").mock(
        return_value=httpx.Response(403, json={"error": {"code": "Forbidden"}})
    )
    r = await probe_virustotal(settings)
    assert r.credential_status == "forbidden"
    assert r.http_status == 403


async def test_crtsh_200_valid(respx_mock, load_fixture, monkeypatch):
    settings = probe_settings(monkeypatch)
    respx_mock.get("https://crt.sh/").mock(
        return_value=httpx.Response(200, json=load_fixture("crtsh_example_com.json"))
    )
    r = await probe_crtsh(settings)
    assert r.credential_status == "valid"
    assert r.probe_scan_status == "used"


async def test_probe_500_unknown(respx_mock, monkeypatch):
    settings = probe_settings(monkeypatch, virustotal="VT")
    respx_mock.get("https://www.virustotal.com/api/v3/domains/example.com").mock(
        return_value=httpx.Response(502, json={"error": "bad gateway"})
    )
    r = await probe_virustotal(settings)
    assert r.credential_status == "unknown"
    assert r.http_status == 502


async def test_sanitize_no_raw_key():
    from globeye.services.source_credential_probe import (
        CredentialProbeResult,
        sanitize_provider_message,
    )

    msg = sanitize_provider_message("api_key=supersecret1234567890abcdef")
    assert "supersecret" not in (msg or "")
    assert "[redacted]" in (msg or "")
    assert CredentialProbeResult("valid", "ok").legacy_status() == "ok"
    assert (
        CredentialProbeResult("keyless", "ok", probe_scan_status="no_results").legacy_status()
        == "ok"
    )


async def test_censys_missing_secret(monkeypatch):
    settings = build_settings(monkeypatch, censys_id="ID")
    r = await probe_censys(settings)
    assert r.credential_status == "missing_key"


async def test_wayback_timeout(respx_mock, monkeypatch):
    settings = build_settings(monkeypatch, wayback_probe_timeout_seconds=0.01)

    def _timeout(_request):
        raise httpx.ReadTimeout("slow")

    respx_mock.get("https://web.archive.org/cdx/search/cdx").mock(side_effect=_timeout)
    r = await probe_wayback(settings)
    assert r.credential_status == "provider_timeout"
