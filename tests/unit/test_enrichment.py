"""Enrichment + pivot derivation (all offline / deterministic)."""

from __future__ import annotations

from globeye.core.models import Confidence, Finding, Target, TargetType
from globeye.core.pivot import derive_pivots
from globeye.enrichment.asn import asn_from_rdap
from globeye.enrichment.geoip import GeoIPEnricher
from globeye.enrichment.reputation import assess


def _f(kind: str, value: str, **kw) -> Finding:
    return Finding(source="s", target="t", confidence=Confidence.LOW, kind=kind, value=value, **kw)


def test_reputation_assess():
    assert assess(_f("breach", "ExampleDB")) == "sensitive"
    assert assess(_f("subdomain", "admin.example.com")) == "notable"
    assert assess(_f("subdomain", "www.example.com")) == "info"


def test_asn_from_rdap():
    assert asn_from_rdap({"handle": "AS64500"}) == 64500
    assert asn_from_rdap({"name": "AS13335"}) == 13335
    assert asn_from_rdap({"handle": "EXAMPLE-DOM"}) is None
    assert asn_from_rdap({}) is None


def test_geoip_disabled_without_db():
    geo = GeoIPEnricher(None, None)
    assert geo.enabled is False
    assert geo.city("192.0.2.1") is None
    assert geo.asn("192.0.2.1") is None
    geo.close()


def test_geoip_missing_file_is_safe():
    geo = GeoIPEnricher("/nonexistent/GeoLite2-City.mmdb", None)
    assert geo.city("192.0.2.1") is None
    geo.close()


def test_derive_pivots_dedup_and_filter():
    pivot_t = Target(raw="x@example.com", type=TargetType.EMAIL, value="x@example.com")
    findings = [
        _f("contact_email", "ABUSE@example.com"),
        _f("email", "x@example.com", pivot_target=pivot_t),
        _f("email", "x@example.com"),  # duplicate value
        _f("username", "octocat"),
        _f("subdomain", "www.example.com"),  # not a pivot
        _f("social_profile", "github:https://github.com/octocat"),  # not a pivot
    ]
    pivots = derive_pivots(findings)
    values = {(t.type.value, t.value) for t in pivots}
    assert ("email", "abuse@example.com") in values
    assert ("email", "x@example.com") in values
    assert ("username", "octocat") in values
    assert all(t.type.value != "domain" for t in pivots)
    assert len(pivots) == 3
