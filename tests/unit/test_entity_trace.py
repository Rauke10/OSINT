"""Entity trace endpoint and grouping (Fase 2C.4)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import Session

from globeye.core.db import make_engine
from globeye.db.models import Entity
from globeye.services.case_data import build_case_data
from globeye.services.entity_trace import build_entity_trace
from globeye.services.url_grouping import classify_wayback_url, wayback_group_summary
from tests.unit.test_case_data import _seed_case


@pytest.fixture
def engine(tmp_path: Path):
    return make_engine(f"sqlite:///{tmp_path}/trace.db")


def test_trace_returns_originals_and_evidence(engine):
    _seed_case(engine)
    payload = build_case_data(engine, 1)
    assert payload["items"]
    eid = payload["items"][0]["id"]
    trace = build_entity_trace(engine, eid)
    assert trace["entity_id"] == eid
    assert trace["original_values"]
    assert "normalized_value" in trace
    assert trace["normalization"]["reason"]
    assert "evidence_ids" in trace


def test_group_does_not_remove_items(engine):
    _seed_case(engine)
    now = datetime.now(UTC)
    with Session(engine) as session:
        for path in ("/files/a.pdf", "/files/b.pdf"):
            session.add(
                Entity(
                    case_id=1,
                    entity_type="url",
                    normalized_value=f"https://example.com{path}",
                    display_value=f"https://example.com{path}",
                    first_seen_at=now,
                    last_seen_at=now,
                    last_job_id=1,
                )
            )
        session.commit()
    data = build_case_data(engine, 1, hide_noisy=False)
    docs = [it for it in data["items"] if "files" in it.get("display_value", "")]
    assert len(docs) >= 2
    groups = wayback_group_summary(data["items"])
    for bucket in groups.values():
        assert bucket["total"] >= 1


def test_admin_login_group_keeps_distinct_urls(engine):
    m1 = classify_wayback_url("https://ex.com/wp-login.php")
    m2 = classify_wayback_url("https://ex.com/admin/panel")
    assert m1.category in {"admin_login", "wordpress"}
    assert m1.group_key != m2.group_key or m1.path_base != m2.path_base


def test_archived_findings_can_exceed_url_entities(engine):
    _seed_case(engine)
    payload = build_case_data(engine, 1)
    c = payload["counts"]
    assert c["findings_total_count"] >= c["total_count"]
    assert c.get("wayback_original_total", c["archived_url_findings_count"]) >= 0
