"""Phase 3 infrastructure sources (HTTP mocked, sanitized fixtures)."""

from __future__ import annotations

import httpx

from globeye.core.target import detect
from globeye.sources.infra.abuseipdb import AbuseIpdbSource
from globeye.sources.infra.censys import CensysSource
from globeye.sources.infra.otx import OtxSource
from globeye.sources.infra.rdap import RdapSource
from globeye.sources.infra.securitytrails import SecurityTrailsSource
from globeye.sources.infra.shodan import ShodanSource
from globeye.sources.infra.virustotal import VirusTotalSource
from globeye.sources.infra.wayback import WaybackSource


async def test_rdap_domain(ctx, load_fixture, respx_mock):
    respx_mock.get("https://rdap.org/domain/example.com").mock(
        return_value=httpx.Response(200, json=load_fixture("rdap_example_com.json"))
    )
    src = RdapSource(ctx)
    findings = await src.fetch(detect("example.com"))
    await src.aclose()

    kinds = {f.kind for f in findings}
    assert "registration" in kinds
    emails = [f for f in findings if f.kind == "contact_email"]
    assert emails
    pivot = emails[0].pivot_target
    assert pivot is not None
    assert pivot.value == "abuse@registrar.example"
    assert ctx.recorder.hosts == {"rdap.org"}


async def test_shodan_requires_key(ctx):
    src = ShodanSource(ctx)
    assert src.available() is False
    assert await src.fetch(detect("example.com")) == []
    await src.aclose()


async def test_shodan_domain(ctx_factory, load_fixture, respx_mock):
    ctx = ctx_factory(shodan_api_key="UNIT-TEST-KEY")
    respx_mock.get("https://api.shodan.io/dns/domain/example.com").mock(
        return_value=httpx.Response(200, json=load_fixture("shodan_dns_example_com.json"))
    )
    src = ShodanSource(ctx)
    findings = await src.fetch(detect("example.com"))
    await src.aclose()

    values = {f.value for f in findings}
    assert "www.example.com" in values
    assert "api.example.com" in values
    assert all("_dmarc" not in v for v in values)
    assert ctx.recorder.hosts == {"api.shodan.io"}


async def test_shodan_host(ctx_factory, load_fixture, respx_mock):
    ctx = ctx_factory(shodan_api_key="UNIT-TEST-KEY")
    respx_mock.get("https://api.shodan.io/shodan/host/192.0.2.10").mock(
        return_value=httpx.Response(200, json=load_fixture("shodan_host.json"))
    )
    src = ShodanSource(ctx)
    findings = await src.fetch(detect("192.0.2.10"))
    await src.aclose()
    assert {f.kind for f in findings} == {"service"}
    assert len(findings) == 2


async def test_censys_host_and_certs(ctx_factory, load_fixture, respx_mock):
    ctx = ctx_factory(censys_api_id="ID", censys_api_secret="SECRET")
    respx_mock.get("https://search.censys.io/api/v2/hosts/192.0.2.10").mock(
        return_value=httpx.Response(200, json=load_fixture("censys_host.json"))
    )
    respx_mock.get("https://search.censys.io/api/v2/certificates/search").mock(
        return_value=httpx.Response(200, json=load_fixture("censys_certs_example_com.json"))
    )
    src = CensysSource(ctx)
    hosts = await src.fetch(detect("192.0.2.10"))
    certs = await src.fetch(detect("example.com"))
    await src.aclose()

    assert len(hosts) == 2
    cert_values = {f.value for f in certs}
    assert "vpn.example.com" in cert_values
    assert "unrelated.test" not in cert_values
    assert ctx.recorder.hosts == {"search.censys.io"}


async def test_securitytrails(ctx_factory, load_fixture, respx_mock):
    ctx = ctx_factory(securitytrails_api_key="ST-KEY")
    respx_mock.get("https://api.securitytrails.com/v1/domain/example.com/subdomains").mock(
        return_value=httpx.Response(200, json=load_fixture("securitytrails_subdomains.json"))
    )
    src = SecurityTrailsSource(ctx)
    findings = await src.fetch(detect("example.com"))
    await src.aclose()
    values = {f.value for f in findings}
    assert "mail.example.com" in values
    assert len(values) == 4


async def test_otx_passive_dns(ctx, load_fixture, respx_mock):
    respx_mock.get(
        "https://otx.alienvault.com/api/v1/indicators/domain/example.com/passive_dns"
    ).mock(return_value=httpx.Response(200, json=load_fixture("otx_passive_dns.json")))
    src = OtxSource(ctx)
    findings = await src.fetch(detect("example.com"))
    await src.aclose()
    values = {f.value for f in findings}
    assert values == {"www.example.com", "mail.example.com"}  # deduped
    assert ctx.recorder.hosts == {"otx.alienvault.com"}


async def test_wayback(ctx, load_fixture, respx_mock):
    respx_mock.get("https://web.archive.org/cdx/search/cdx").mock(
        return_value=httpx.Response(200, json=load_fixture("wayback_cdx.json"))
    )
    src = WaybackSource(ctx)
    findings = await src.fetch(detect("example.com"))
    await src.aclose()
    kinds = {f.kind for f in findings}
    assert "wayback_summary" in kinds
    urls = {f.value for f in findings if f.kind == "archived_url"}
    assert urls == {
        "http://example.com/",
        "http://example.com/login",
        "http://example.com/admin",
    }


async def test_abuseipdb_requires_key(ctx):
    src = AbuseIpdbSource(ctx)
    assert src.available() is False
    assert await src.fetch(detect("192.0.2.10")) == []
    await src.aclose()


async def test_abuseipdb_check(ctx_factory, load_fixture, respx_mock):
    ctx = ctx_factory(abuseipdb_api_key="ABUSE-KEY")
    respx_mock.get("https://api.abuseipdb.com/api/v2/check").mock(
        return_value=httpx.Response(200, json=load_fixture("abuseipdb_check.json"))
    )
    src = AbuseIpdbSource(ctx)
    findings = await src.fetch(detect("192.0.2.10"))
    await src.aclose()
    assert len(findings) == 1
    assert findings[0].kind == "ip_reputation"
    assert "42" in findings[0].value
    assert ctx.recorder.hosts == {"api.abuseipdb.com"}


async def test_virustotal_domain(ctx_factory, load_fixture, respx_mock):
    ctx = ctx_factory(virustotal_api_key="VT-KEY")
    respx_mock.get("https://www.virustotal.com/api/v3/domains/example.com").mock(
        return_value=httpx.Response(200, json=load_fixture("virustotal_domain_example_com.json"))
    )
    src = VirusTotalSource(ctx)
    findings = await src.fetch(detect("example.com"))
    await src.aclose()
    kinds = {f.kind for f in findings}
    assert "analysis_stats" in kinds
    assert "resolution" in kinds
    assert "cname" in kinds
    assert ctx.recorder.hosts == {"www.virustotal.com"}


async def test_virustotal_ip(ctx_factory, load_fixture, respx_mock):
    ctx = ctx_factory(virustotal_api_key="VT-KEY")
    respx_mock.get("https://www.virustotal.com/api/v3/ip_addresses/192.0.2.10").mock(
        return_value=httpx.Response(200, json=load_fixture("virustotal_ip.json"))
    )
    src = VirusTotalSource(ctx)
    findings = await src.fetch(detect("192.0.2.10"))
    await src.aclose()
    assert {f.kind for f in findings} >= {"analysis_stats", "hostname"}
    assert "mail.example.com" in {f.value for f in findings}
