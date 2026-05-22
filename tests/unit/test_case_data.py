"""Case data explorer service (Fase 2C)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlmodel import Session

from globeye.core.db import make_engine, save_scan
from globeye.core.models import Confidence, Finding, GraphNodeHint, ScanResult, Target, TargetType
from globeye.core.target import detect
from globeye.db.models import Case, ScanJob
from globeye.services.case_data import build_case_data, explorer_type
from globeye.services.entity_normalizer import persist_entities_from_scan
from globeye.services.finding_quality import QualityLabel, annotate_scan_result


@pytest.fixture
def engine(tmp_path: Path):
    return make_engine(f"sqlite:///{tmp_path}/case_data.db")


def _seed_case(engine, case_id: int = 1, job_id: int = 1) -> None:
    target = detect("example.com")
    findings = [
        Finding(
            source="crtsh",
            target="example.com",
            confidence=Confidence.HIGH,
            kind="subdomain",
            value="api.example.com",
        ),
        Finding(
            source="rdap",
            target="example.com",
            confidence=Confidence.HIGH,
            kind="subdomain",
            value="api.example.com",
        ),
        Finding(
            source="wayback",
            target="example.com",
            confidence=Confidence.LOW,
            kind="archived_url",
            value="http://example.com/old",
            normalized_data={"wayback_index": 0, "wayback_total": 100},
            graph_node_hint=GraphNodeHint(
                node_type="url",
                node_id="http://example.com/old",
                label="http://example.com/old",
                parent_id="example.com",
            ),
        ),
    ]
    result = ScanResult(
        target=target,
        started_at=findings[0].timestamp,
        finished_at=findings[0].timestamp,
        sources_used=["crtsh", "rdap"],
        findings=findings,
    )
    annotate_scan_result(result)
    with Session(engine) as session:
        session.add(Case(id=case_id, title="Test", status="open"))
        session.add(
            ScanJob(
                id=job_id,
                case_id=case_id,
                target_raw=target.raw,
                target_type=target.type.value,
                target_value=target.value,
                status="completed",
            )
        )
        session.commit()
    scan_id = save_scan(engine, result)
    with Session(engine) as session:
        job = session.get(ScanJob, job_id)
        if job:
            job.scan_record_id = scan_id
            session.add(job)
            session.commit()
    persist_entities_from_scan(engine, case_id=case_id, job_id=job_id, result=result)


def test_explorer_type_aliases():
    assert explorer_type("org") == "organization"
    assert explorer_type("archived_url") == "url"


def test_build_case_data_summary_and_types(engine):
    _seed_case(engine)
    payload = build_case_data(engine, 1, hide_noisy=False, hide_false_positive=False)
    assert payload["summary"]["total_items"] >= 2
    assert payload["summary"].get("subdomain", 0) >= 1
    types = {it["type"] for it in payload["items"]}
    assert "subdomain" in types


def test_filter_by_type(engine):
    _seed_case(engine)
    payload = build_case_data(engine, 1, type_filter="subdomain", hide_noisy=False)
    assert all(it["type"] == "subdomain" for it in payload["items"])


def test_filter_by_quality_verified(engine):
    _seed_case(engine)
    payload = build_case_data(
        engine, 1, quality_filter="verified", hide_noisy=False, hide_false_positive=False
    )
    assert payload["total"] >= 1
    assert all(it["quality_label"] == "verified" for it in payload["items"])


def test_hide_noisy_hides_historical_items(engine):
    _seed_case(engine)
    from datetime import UTC, datetime

    from globeye.db.models import Entity

    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            Entity(
                case_id=1,
                entity_type="url",
                normalized_value="http://example.com/legacy-path-only",
                display_value="http://example.com/legacy-path-only",
                first_seen_at=now,
                last_seen_at=now,
                last_job_id=1,
            )
        )
        session.commit()
    all_rows = build_case_data(engine, 1, hide_noisy=False, hide_false_positive=False)
    hidden = build_case_data(
        engine, 1, hide_historical=True, hide_noisy=False, hide_false_positive=False
    )
    assert hidden["total"] < all_rows["total"]
    assert hidden["counts"]["hidden_historical_count"] >= 1


def test_hide_false_positive(engine):
    _seed_case(engine, job_id=2)
    target = Target(raw="x", type=TargetType.DOMAIN, value="example.com")
    fp = Finding(
        source="github",
        target="example.com",
        confidence=Confidence.LOW,
        kind="subdomain",
        value="examp1e.com",
    )
    result = ScanResult(
        target=target,
        started_at=fp.timestamp,
        finished_at=fp.timestamp,
        sources_used=["github"],
        findings=[fp],
    )
    annotate_scan_result(result)
    persist_entities_from_scan(engine, case_id=1, job_id=2, result=result)

    payload = build_case_data(engine, 1, hide_noisy=False, hide_false_positive=True)
    labels = {it["quality_label"] for it in payload["items"]}
    assert QualityLabel.POSSIBLE_FALSE_POSITIVE.value not in labels


def test_filter_by_source(engine):
    _seed_case(engine)
    payload = build_case_data(engine, 1, source_filter="crtsh", hide_noisy=False)
    assert payload["total"] >= 1
    assert all("crtsh" in it["sources"] for it in payload["items"])


def test_evidence_count_field(engine):
    _seed_case(engine)
    payload = build_case_data(engine, 1, hide_noisy=False)
    for it in payload["items"]:
        assert "evidence_count" in it
        assert isinstance(it["evidence_count"], int)
