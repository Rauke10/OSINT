"""End-to-end scan with every relevant source mocked, including a pivot."""

from __future__ import annotations

import httpx
import pytest

from globeye.config import Settings
from globeye.core.context import ScanContext
from globeye.core.orchestrator import Orchestrator

pytestmark = pytest.mark.e2e


async def test_full_domain_scan_with_pivot(tmp_path, load_fixture, respx_mock):
    settings = Settings(
        _env_file=None,
        cache_enabled=False,
        http_max_retries=0,
        shodan_api_key="K",
        securitytrails_api_key="K",
        hunter_api_key="K",
        github_token="ghp_" + "x" * 30,
        hibp_api_key="K",
        db_url=f"sqlite:///{tmp_path}/e2e.db",
    )
    ctx = ScanContext.create(settings)

    # Domain-applicable sources.
    respx_mock.get("https://crt.sh/").mock(
        return_value=httpx.Response(200, json=load_fixture("crtsh_example_com.json"))
    )
    respx_mock.get("https://rdap.org/domain/example.com").mock(
        return_value=httpx.Response(200, json=load_fixture("rdap_example_com.json"))
    )
    respx_mock.get(
        "https://otx.alienvault.com/api/v1/indicators/domain/example.com/passive_dns"
    ).mock(return_value=httpx.Response(200, json=load_fixture("otx_passive_dns.json")))
    respx_mock.get("https://web.archive.org/cdx/search/cdx").mock(
        return_value=httpx.Response(200, json=load_fixture("wayback_cdx.json"))
    )
    respx_mock.get("https://api.shodan.io/dns/domain/example.com").mock(
        return_value=httpx.Response(200, json=load_fixture("shodan_dns_example_com.json"))
    )
    respx_mock.get("https://api.securitytrails.com/v1/domain/example.com/subdomains").mock(
        return_value=httpx.Response(200, json=load_fixture("securitytrails_subdomains.json"))
    )
    respx_mock.get("https://api.hunter.io/v2/domain-search").mock(
        return_value=httpx.Response(200, json=load_fixture("hunter_domain.json"))
    )
    respx_mock.get("https://api.github.com/search/code").mock(
        return_value=httpx.Response(200, json=load_fixture("github_code.json"))
    )
    # Pivot: Hunter yields jane.doe@example.com -> HIBP runs on the email.
    respx_mock.get("https://haveibeenpwned.com/api/v3/breachedaccount/jane.doe@example.com").mock(
        return_value=httpx.Response(200, json=load_fixture("hibp_breaches.json"))
    )
    respx_mock.route(host="info@example.com").pass_through()  # never used
    respx_mock.get("https://haveibeenpwned.com/api/v3/breachedaccount/info@example.com").mock(
        return_value=httpx.Response(404)
    )

    result = await Orchestrator(settings, ctx).scan("example.com", pivot=True)

    used = set(result.sources_used)
    assert {"crtsh", "rdap", "otx", "wayback", "shodan", "securitytrails", "hunter"} <= used
    # Pivoted from a discovered email and ran HIBP on it.
    assert any(t.value == "jane.doe@example.com" for t in result.pivoted_targets)
    assert any(f.source == "hibp" and f.kind == "breach" for f in result.findings)
    # The passive invariant still holds end to end.
    assert "example.com" not in {httpx.URL(u).host for u in ctx.recorder.urls if "crt.sh" not in u}
