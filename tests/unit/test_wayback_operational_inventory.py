"""Wayback URLs are fully operable in Data Explorer (Fase 2C.4 inventory)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import Session

from globeye.core.db import make_engine, save_scan
from globeye.core.models import Confidence, Finding, GraphNodeHint, ScanResult
from globeye.core.target import detect
from globeye.db.models import Case, Entity, ScanJob
from globeye.services.case_data import build_case_data
from globeye.services.entity_normalizer import persist_entities_from_scan
from globeye.services.finding_quality import annotate_scan_result
from globeye.services.url_live_check import MAX_BATCH_URLS
from globeye.sources.infra.wayback import WAYBACK_FINDINGS_PER_SCAN


@pytest.fixture
def engine(tmp_path: Path):
    return make_engine(f"sqlite:///{tmp_path}/wb_inv.db")


def _scan_with_wayback_urls(engine, n: int = 100) -> int:
    """Persist a scan with n distinct Wayback archived_url findings (all with graph hints)."""
    target = detect("example.com")
    now = datetime.now(UTC)
    findings: list[Finding] = [
        Finding(
            source="wayback",
            target="example.com",
            confidence=Confidence.LOW,
            kind="archived_url",
            value=f"https://example.com/path/{i}/page",
            normalized_data={"wayback_index": i, "wayback_total": n},
            graph_node_hint=GraphNodeHint(
                node_type="url",
                node_id=f"https://example.com/path/{i}/page",
                label=f"https://example.com/path/{i}/page",
                parent_id="example.com",
            ),
        )
        for i in range(n)
    ]
    result = ScanResult(
        target=target,
        started_at=now,
        finished_at=now,
        sources_used=["wayback"],
        findings=findings,
    )
    annotate_scan_result(result)
    with Session(engine) as session:
        session.add(Case(id=1, title="WB", status="open"))
        session.add(
            ScanJob(
                id=1,
                case_id=1,
                target_raw=target.raw,
                target_type=target.type.value,
                target_value=target.value,
                status="completed",
            )
        )
        session.commit()
    scan_id = save_scan(engine, result)
    with Session(engine) as session:
        job = session.get(ScanJob, 1)
        if job:
            job.scan_record_id = scan_id
            session.add(job)
            session.commit()
    persist_entities_from_scan(engine, case_id=1, job_id=1, result=result)
    return n


def test_all_wayback_urls_become_entities(engine):
    from sqlmodel import select

    n = 80
    _scan_with_wayback_urls(engine, n)
    with Session(engine) as session:
        stmt = select(Entity).where(Entity.case_id == 1, Entity.entity_type == "url")
        rows = list(session.exec(stmt).all())
    assert len(rows) == n


def test_data_explorer_lists_wayback_urls_paginated(engine):
    n = 100
    _scan_with_wayback_urls(engine, n)
    page = build_case_data(
        engine, 1, type_filter="url", inventory_status_filter="all", limit=25, offset=0
    )
    assert page["visible_count"] == 25
    assert page["filtered_count"] == n
    assert page["total_count"] >= n
    assert page["counts"]["wayback_live_check_batch_limit"] == MAX_BATCH_URLS
    assert page["counts"]["wayback_scan_url_cap"] == WAYBACK_FINDINGS_PER_SCAN

    page2 = build_case_data(
        engine, 1, type_filter="url", inventory_status_filter="all", limit=25, offset=25
    )
    assert len(page2["items"]) == 25
    assert page2["filtered_count"] == n


def test_entity_limit_does_not_cap_inventory(engine):
    _scan_with_wayback_urls(engine, 50)
    payload = build_case_data(engine, 1, inventory_status_filter="all", limit=2000)
    c = payload["counts"]
    assert c["url_entity_count"] >= 50
    assert c["archived_url_findings_count"] >= 50
    assert c["wayback_entity_limit"] == MAX_BATCH_URLS


def test_distinct_wayback_paths_stay_separate(engine):
    _scan_with_wayback_urls(engine, 2)
    payload = build_case_data(engine, 1, type_filter="url", inventory_status_filter="all", limit=10)
    values = {it["normalized_value"] for it in payload["items"]}
    assert len(values) == 2


def test_discard_wayback_url_beyond_first_25(engine):
    from globeye.services.entity_review import bulk_review

    n = 60
    _scan_with_wayback_urls(engine, n)
    all_rows = build_case_data(
        engine, 1, type_filter="url", inventory_status_filter="all", limit=2000
    )["items"]
    assert len(all_rows) >= 50
    late_id = all_rows[40]["id"]
    bulk_review(
        engine,
        case_id=1,
        entity_ids=[late_id],
        review_status="discarded",
        hidden=True,
        hidden_reason="test discard",
    )
    hidden = build_case_data(
        engine,
        1,
        type_filter="url",
        inventory_status_filter="pending",
        hide_discarded=True,
        limit=2000,
    )
    assert late_id not in {it["id"] for it in hidden["items"]}
    full = build_case_data(engine, 1, type_filter="url", inventory_status_filter="all", limit=2000)
    late = next(it for it in full["items"] if it["id"] == late_id)
    assert late["hidden"] is True


def test_live_check_entity_exists_beyond_first_25(engine):
    from sqlmodel import select

    n = 40
    _scan_with_wayback_urls(engine, n)
    with Session(engine) as session:
        entities = list(
            session.exec(
                select(Entity).where(Entity.case_id == 1, Entity.entity_type == "url")
            ).all()
        )
    assert len(entities) == n
    payload = build_case_data(engine, 1, type_filter="url", limit=2000)
    row_30 = payload["items"][30]
    assert row_30["is_wayback_url"]
    assert row_30["id"] > 0
