"""EnrichmentPipeline: reputation tagging + GeoIP (offline)."""

from __future__ import annotations

from globeye.config import Settings
from globeye.core.models import Confidence, Finding
from globeye.enrichment.pipeline import EnrichmentPipeline, finding_ip


def _f(kind: str, value: str, target: str = "example.com") -> Finding:
    return Finding(source="s", target=target, confidence=Confidence.LOW, kind=kind, value=value)


def test_pipeline_tags_reputation_in_place():
    findings = [
        _f("breach", "ExampleDB"),
        _f("subdomain", "admin.example.com"),
        _f("subdomain", "www.example.com"),
    ]
    out = EnrichmentPipeline(Settings(_env_file=None)).run(findings)
    assert out is findings  # annotated in place
    assert findings[0].normalized_data["reputation"] == "sensitive"
    assert findings[1].normalized_data["reputation"] == "notable"
    assert findings[2].normalized_data["reputation"] == "info"


def test_pipeline_skips_geo_without_databases():
    f = _f("service", "192.0.2.10:443", target="192.0.2.10")
    EnrichmentPipeline(Settings(_env_file=None)).run([f])
    assert "reputation" in f.normalized_data
    assert "geo" not in f.normalized_data  # no .mmdb configured -> no geo block


def test_finding_ip_extracts_addresses():
    assert finding_ip(_f("service", "192.0.2.10:443", target="192.0.2.10")) == "192.0.2.10"
    assert finding_ip(_f("subdomain", "www.example.com")) is None
