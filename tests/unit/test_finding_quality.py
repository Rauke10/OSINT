"""Finding quality classification (Fase 2B.1)."""

from __future__ import annotations

from globeye.core.models import Confidence, Finding
from globeye.core.target import detect
from globeye.services.finding_quality import (
    QualityLabel,
    _entity_key,
    _source_groups,
    annotate_findings,
    classify_finding,
)


def _f(
    source: str,
    kind: str,
    value: str,
    *,
    confidence: Confidence = Confidence.MEDIUM,
) -> Finding:
    return Finding(
        source=source,
        target="example.com",
        confidence=confidence,
        kind=kind,
        value=value,
    )


def test_two_sources_verified():
    findings = [
        _f("crtsh", "subdomain", "api.example.com"),
        _f("securitytrails", "subdomain", "api.example.com"),
    ]
    target = detect("example.com")
    groups = _source_groups(findings)
    meta = classify_finding(findings[0], target=target, source_counts=groups)
    assert meta.quality_label == QualityLabel.VERIFIED.value
    assert meta.verification_sources_count == 2


def test_wayback_historical():
    findings = [
        Finding(
            source="wayback",
            target="example.com",
            confidence=Confidence.LOW,
            kind="archived_url",
            value="http://example.com/old",
            normalized_data={"wayback_truncated": True, "wayback_total": 500},
        )
    ]
    target = detect("example.com")
    meta = classify_finding(
        findings[0], target=target, source_counts=_source_groups(findings), wayback_total=500
    )
    assert meta.quality_label in {QualityLabel.HISTORICAL.value, QualityLabel.NOISY.value}
    assert meta.is_historical


def test_single_trusted_likely():
    findings = [_f("rdap", "registration", "EXAMPLE", confidence=Confidence.HIGH)]
    target = detect("example.com")
    meta = classify_finding(findings[0], target=target, source_counts=_source_groups(findings))
    assert meta.quality_label == QualityLabel.LIKELY.value


def test_single_source_unverified():
    findings = [_f("github", "code_match", "snippet", confidence=Confidence.LOW)]
    target = detect("example.com")
    meta = classify_finding(findings[0], target=target, source_counts=_source_groups(findings))
    assert meta.quality_label in {
        QualityLabel.UNVERIFIED.value,
        QualityLabel.NOISY.value,
        QualityLabel.POSSIBLE_FALSE_POSITIVE.value,
    }


def test_wayback_bulk_noisy():
    target = detect("example.com")
    findings = [
        Finding(
            source="wayback",
            target="example.com",
            confidence=Confidence.LOW,
            kind="archived_url",
            value=f"http://example.com/{i}",
            normalized_data={"wayback_index": i, "wayback_total": 201},
        )
        for i in range(60)
    ]
    meta = classify_finding(
        findings[0], target=target, source_counts=_source_groups(findings), wayback_total=201
    )
    assert meta.quality_label == QualityLabel.NOISY.value


def test_similar_domain_false_positive():
    findings = [_f("crtsh", "subdomain", "examp1e.com")]
    target = detect("example.com")
    meta = classify_finding(findings[0], target=target, source_counts=_source_groups(findings))
    assert meta.quality_label == QualityLabel.POSSIBLE_FALSE_POSITIVE.value
    assert meta.is_potential_false_positive


def test_entity_key_case_insensitive():
    assert _entity_key("email", "Test@Example.COM") == ("email", "test@example.com")


def test_annotate_findings_attaches_quality():
    findings = [_f("rdap", "registration", "EXAMPLE", confidence=Confidence.HIGH)]
    target = detect("example.com")
    out = annotate_findings(findings, target)
    assert "quality" in out[0].normalized_data
    assert out[0].normalized_data["quality"]["quality_label"]
