"""Shared API dependencies."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.engine import Engine
from sqlmodel import Session, func, select

from globeye.db.models import Case, CaseTarget, Entity, ScanJob


def get_case_or_404(engine: Engine, case_id: int) -> Case:
    with Session(engine) as session:
        case = session.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="case not found")
    return case


def case_counts(engine: Engine, case_id: int) -> tuple[int, int, int]:
    with Session(engine) as session:
        targets = session.exec(
            select(func.count()).select_from(CaseTarget).where(CaseTarget.case_id == case_id)
        ).one()
        jobs = session.exec(
            select(func.count()).select_from(ScanJob).where(ScanJob.case_id == case_id)
        ).one()
        entities = session.exec(
            select(func.count()).select_from(Entity).where(Entity.case_id == case_id)
        ).one()
    return int(targets), int(jobs), int(entities)
