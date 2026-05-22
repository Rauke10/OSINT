"""Case deletion (Fase 2D)."""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlmodel import Session, col, delete

from globeye.db.models import (
    Case,
    CaseTarget,
    Entity,
    EntityRelationship,
    EntityReview,
    ScanJob,
    SourceResult,
    StoredEvidence,
    UrlLiveCheck,
)


def delete_case(engine: Engine, case_id: int) -> None:
    """Permanently delete a case and associated rows."""
    with Session(engine) as session:
        session.exec(delete(EntityReview).where(col(EntityReview.case_id) == case_id))
        session.exec(delete(UrlLiveCheck).where(col(UrlLiveCheck.case_id) == case_id))
        session.exec(delete(StoredEvidence).where(col(StoredEvidence.case_id) == case_id))
        session.exec(delete(SourceResult).where(col(SourceResult.case_id) == case_id))
        session.exec(delete(EntityRelationship).where(col(EntityRelationship.case_id) == case_id))
        session.exec(delete(Entity).where(col(Entity.case_id) == case_id))
        session.exec(delete(ScanJob).where(col(ScanJob.case_id) == case_id))
        session.exec(delete(CaseTarget).where(col(CaseTarget.case_id) == case_id))
        session.exec(delete(Case).where(col(Case.id) == case_id))
        session.commit()
