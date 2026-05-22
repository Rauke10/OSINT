"""Case data filters for Fase 2C.3."""

from __future__ import annotations

from sqlmodel import Session

from globeye.core.db import make_engine
from globeye.db.models import Case, Entity
from globeye.services.case_data import build_case_data
from globeye.services.entity_review import upsert_review


def _url_entity(engine, case_id: int, url: str) -> int:
    with Session(engine) as session:
        ent = Entity(
            case_id=case_id,
            entity_type="archived_url",
            normalized_value=url,
            display_value=url,
            last_job_id=1,
        )
        session.add(ent)
        session.commit()
        session.refresh(ent)
        return int(ent.id or 0)


def test_operational_status_discarded(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/f.db")
    with Session(engine) as s:
        case = Case(title="F")
        s.add(case)
        s.commit()
        s.refresh(case)
        cid = int(case.id or 0)
    eid = _url_entity(engine, cid, "https://ex.com/admin")
    upsert_review(engine, cid, entity_id=eid, hidden=True, review_status="discarded")
    data = build_case_data(
        engine,
        cid,
        operational_status_filter="discarded",
        inventory_status_filter="discarded",
        hide_discarded=False,
    )
    assert data["total"] >= 1


def test_wayback_priority_high_filter(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/f2.db")
    with Session(engine) as s:
        case = Case(title="F2")
        s.add(case)
        s.commit()
        s.refresh(case)
        cid = int(case.id or 0)
    _url_entity(engine, cid, "https://ex.com/wp-admin/")
    _url_entity(engine, cid, "https://ex.com/about.html")
    data = build_case_data(
        engine,
        cid,
        wayback_priority="high",
        inventory_status_filter="all",
        hide_discarded=False,
        hide_noisy=False,
    )
    for it in data["items"]:
        assert it.get("wayback_priority") == "high"
