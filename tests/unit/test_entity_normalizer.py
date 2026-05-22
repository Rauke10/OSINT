"""Unit tests for entity normalization from scan results."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Session, select

from globeye.core.db import make_engine
from globeye.core.models import (
    Confidence,
    Finding,
    GraphNodeHint,
    ScanResult,
    Target,
    TargetType,
)
from globeye.db.models import Entity, EntityRelationship
from globeye.services.entity_normalizer import build_case_graph, persist_entities_from_scan


def _domain_result() -> ScanResult:
    target = Target(raw="example.com", type=TargetType.DOMAIN, value="example.com")
    now = datetime.now(UTC)
    return ScanResult(
        target=target,
        started_at=now,
        finished_at=now,
        sources_used=["crtsh"],
        findings=[
            Finding(
                source="crtsh",
                target="example.com",
                confidence=Confidence.HIGH,
                kind="subdomain",
                value="api.example.com",
                graph_node_hint=GraphNodeHint(
                    node_type="subdomain",
                    node_id="api.example.com",
                    label="api.example.com",
                    parent_id="example.com",
                ),
            ),
            Finding(
                source="rdap",
                target="example.com",
                confidence=Confidence.MEDIUM,
                kind="registrar",
                value="Example Registrar",
            ),
        ],
    )


def test_persist_entities_and_relationships(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/norm.db")
    from globeye.db.models import Case

    with Session(engine) as session:
        session.add(Case(title="Norm", status="open"))
        session.commit()

    result = _domain_result()
    e_count, r_count = persist_entities_from_scan(engine, case_id=1, job_id=1, result=result)
    assert e_count >= 2
    assert r_count >= 1

    with Session(engine) as session:
        entities = list(session.exec(select(Entity).where(Entity.case_id == 1)).all())
        rels = list(
            session.exec(select(EntityRelationship).where(EntityRelationship.case_id == 1)).all()
        )
    assert len(entities) >= 2
    assert len(rels) >= 1
    values = {e.normalized_value for e in entities}
    assert "example.com" in values
    assert "api.example.com" in values


def test_upsert_updates_last_seen(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/upsert.db")
    # case_id=1 requires case table - create minimal case via raw insert
    from globeye.db.models import Case

    with Session(engine) as session:
        session.add(Case(title="Test", status="open"))
        session.commit()

    result = _domain_result()
    persist_entities_from_scan(engine, case_id=1, job_id=1, result=result)
    with Session(engine) as session:
        first = session.exec(select(Entity).where(Entity.case_id == 1)).all()
        first_seen = {e.normalized_value: e.last_seen_at for e in first}

    persist_entities_from_scan(engine, case_id=1, job_id=2, result=result)
    with Session(engine) as session:
        second = list(session.exec(select(Entity).where(Entity.case_id == 1)).all())
    assert len(second) == len(first)
    for ent in second:
        if ent.normalized_value in first_seen:
            assert ent.last_seen_at >= first_seen[ent.normalized_value]


def test_build_case_graph(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/graph.db")
    from globeye.db.models import Case

    with Session(engine) as session:
        session.add(Case(title="Graph test", status="open"))
        session.commit()

    persist_entities_from_scan(engine, case_id=1, job_id=1, result=_domain_result())
    graph_all = build_case_graph(engine, 1, mode="all")
    assert len(graph_all["nodes"]) >= 2
    assert len(graph_all["edges"]) >= 1
    graph_inv = build_case_graph(engine, 1, mode="inventory")
    assert len(graph_inv["nodes"]) == 0
