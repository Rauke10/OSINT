"""Entity review / discard tests (Fase 2C.3)."""

from __future__ import annotations

from sqlmodel import Session

from globeye.core.db import make_engine
from globeye.db.models import Case, Entity
from globeye.services.case_data import build_case_data
from globeye.services.entity_review import bulk_review, upsert_review


def _seed(engine, url: str = "https://example.com/old") -> tuple[int, int]:
    with Session(engine) as session:
        case = Case(title="Review test")
        session.add(case)
        session.commit()
        session.refresh(case)
        cid = int(case.id or 0)
        ent = Entity(
            case_id=cid,
            entity_type="url",
            normalized_value=url,
            display_value=url,
            last_job_id=1,
        )
        session.add(ent)
        session.commit()
        session.refresh(ent)
        return cid, int(ent.id or 0)


def test_discard_hides_from_data(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/rev.db")
    case_id, eid = _seed(engine)
    upsert_review(
        engine,
        case_id,
        entity_id=eid,
        review_status="discarded",
        hidden=True,
        hidden_reason="404 not found",
    )
    visible = build_case_data(engine, case_id, hide_discarded=True)
    assert visible["total"] == 0
    all_rows = build_case_data(
        engine, case_id, hide_discarded=False, inventory_status_filter="discarded"
    )
    assert all_rows["total"] == 1
    assert all_rows["items"][0]["review_status"] == "discarded"


def test_restore_discarded(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/rev2.db")
    case_id, eid = _seed(engine)
    upsert_review(engine, case_id, entity_id=eid, hidden=True, review_status="discarded")
    upsert_review(
        engine,
        case_id,
        entity_id=eid,
        hidden=False,
        review_status="reviewed",
    )
    data = build_case_data(engine, case_id, hide_discarded=True, inventory_status_filter="pending")
    assert data["total"] == 1
    assert data["items"][0]["hidden"] is False


def test_bulk_discard(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/rev3.db")
    case_id, eid = _seed(engine)
    out = bulk_review(engine, case_id, entity_ids=[eid], hidden_reason="bulk")
    assert out["updated"] == 1
