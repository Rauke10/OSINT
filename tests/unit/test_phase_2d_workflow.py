"""Fase 2D: inventario manual, bandeja pendiente, paginación y live check web."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import Session, select

from globeye.core.db import make_engine, save_scan
from globeye.core.models import Confidence, Finding, GraphNodeHint, ScanResult
from globeye.core.target import detect
from globeye.db.models import Case, EntityReview, ScanJob
from globeye.services.case_data import build_case_data
from globeye.services.case_delete import delete_case
from globeye.services.case_inventory import build_case_inventory
from globeye.services.entity_normalizer import build_case_graph, persist_entities_from_scan
from globeye.services.entity_review import (
    approve_entities,
    bulk_review,
    discard_entities,
    remove_from_inventory,
    restore_entities,
    set_inventory_approval,
)
from globeye.services.finding_quality import annotate_scan_result
from globeye.services.url_live_check import url_for_entity_check


@pytest.fixture
def engine(tmp_path: Path):
    return make_engine(f"sqlite:///{tmp_path}/phase2d.db")


def _seed_url_entities(engine, n: int = 3) -> list[int]:
    target = detect("example.com")
    now = datetime.now(UTC)
    findings = [
        Finding(
            source="wayback",
            target="example.com",
            confidence=Confidence.LOW,
            kind="archived_url",
            value=f"https://example.com/p/{i}",
            graph_node_hint=GraphNodeHint(
                node_type="url",
                node_id=f"https://example.com/p/{i}",
                label=f"https://example.com/p/{i}",
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
        session.add(Case(id=1, title="T", status="open"))
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
    payload = build_case_data(engine, 1, type_filter="url", inventory_status_filter="all", limit=50)
    return [it["id"] for it in payload["items"]]


def test_approve_entity_appears_in_inventory(engine):
    ids = _seed_url_entities(engine, 2)
    approve_entities(engine, 1, [ids[0]])
    inv = build_case_inventory(engine, 1, limit=50)
    assert inv["filtered_count"] == 1
    assert inv["items"][0]["approved_for_inventory"] is True
    assert inv["items"][0]["hidden"] is False
    assert inv["items"][0]["review_status"] == "reviewed"


def test_approved_hidden_from_default_raw_data(engine):
    ids = _seed_url_entities(engine, 2)
    approve_entities(engine, 1, [ids[0]])
    pending = build_case_data(engine, 1, type_filter="url", inventory_status_filter="pending")
    assert ids[0] not in {it["id"] for it in pending["items"]}
    assert pending["filtered_count"] == 1


def test_approved_visible_with_approved_filter(engine):
    ids = _seed_url_entities(engine, 2)
    approve_entities(engine, 1, [ids[0]])
    approved = build_case_data(engine, 1, type_filter="url", inventory_status_filter="approved")
    assert ids[0] in {it["id"] for it in approved["items"]}


def test_approve_never_marks_discarded(engine):
    ids = _seed_url_entities(engine, 1)
    approve_entities(engine, 1, [ids[0]])
    with Session(engine) as session:
        row = session.exec(select(EntityReview).where(EntityReview.entity_id == ids[0])).first()
    assert row is not None
    assert row.hidden is False
    assert row.review_status == "reviewed"
    assert row.approved_for_inventory is True
    assert row.inventory_status == "approved"


def test_bulk_approve_action_not_discarded(engine):
    ids = _seed_url_entities(engine, 1)
    bulk_review(engine, 1, entity_ids=[ids[0]], action="approve")
    with Session(engine) as session:
        row = session.exec(select(EntityReview).where(EntityReview.entity_id == ids[0])).first()
    assert row is not None
    assert row.hidden is False
    assert row.review_status != "discarded"


def test_remove_from_inventory_returns_to_pending(engine):
    ids = _seed_url_entities(engine, 1)
    approve_entities(engine, 1, [ids[0]])
    remove_from_inventory(engine, 1, [ids[0]])
    pending = build_case_data(engine, 1, type_filter="url", inventory_status_filter="pending")
    assert ids[0] in {it["id"] for it in pending["items"]}
    inv = build_case_inventory(engine, 1, limit=10)
    assert inv["filtered_count"] == 0


def test_discard_approved_removes_from_inventory(engine):
    ids = _seed_url_entities(engine, 1)
    approve_entities(engine, 1, [ids[0]])
    discard_entities(engine, 1, [ids[0]], hidden_reason="test")
    inv = build_case_inventory(engine, 1, limit=10)
    assert inv["filtered_count"] == 0
    discarded = build_case_data(engine, 1, type_filter="url", inventory_status_filter="discarded")
    assert ids[0] in {it["id"] for it in discarded["items"]}


def test_restore_discarded_does_not_auto_approve(engine):
    ids = _seed_url_entities(engine, 1)
    discard_entities(engine, 1, [ids[0]], hidden_reason="x")
    restore_entities(engine, 1, [ids[0]])
    with Session(engine) as session:
        row = session.exec(select(EntityReview).where(EntityReview.entity_id == ids[0])).first()
    assert row is not None
    assert row.approved_for_inventory is False
    assert row.hidden is False


def test_404_url_can_be_approved_manually(engine):
    ids = _seed_url_entities(engine, 1)
    set_inventory_approval(engine, 1, ids[0], approved=True)
    inv = build_case_inventory(engine, 1, limit=10)
    assert inv["items"][0]["approved_for_inventory"] is True


def test_data_pagination_distinct_pages(engine):
    _seed_url_entities(engine, 30)
    p0 = build_case_data(
        engine, 1, type_filter="url", inventory_status_filter="all", limit=10, offset=0
    )
    p1 = build_case_data(
        engine, 1, type_filter="url", inventory_status_filter="all", limit=10, offset=10
    )
    assert len(p0["items"]) == 10
    assert len(p1["items"]) == 10
    assert {it["id"] for it in p0["items"]}.isdisjoint({it["id"] for it in p1["items"]})


def test_domain_check_url_builder():
    assert url_for_entity_check("domain", "example.com", "example.com") == "https://example.com"
    assert (
        url_for_entity_check("subdomain", "api.example.com", "api.example.com")
        == "https://api.example.com"
    )


def test_graph_default_inventory_mode(engine):
    ids = _seed_url_entities(engine, 2)
    approve_entities(engine, 1, [ids[0]])
    g_inv = build_case_graph(engine, 1, mode="inventory")
    g_all = build_case_graph(engine, 1, mode="all")
    assert len(g_inv["nodes"]) <= len(g_all["nodes"])


def test_delete_case_removes_data(engine):
    _seed_url_entities(engine, 2)
    delete_case(engine, 1)
    with Session(engine) as session:
        assert session.get(Case, 1) is None
