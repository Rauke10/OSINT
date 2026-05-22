"""Scan job endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Engine
from sqlmodel import Session, select
from starlette.concurrency import run_in_threadpool

from globeye.api.auth import get_engine, require_api_key
from globeye.api.deps import get_case_or_404
from globeye.api.schemas.cases import JobDetail, JobSummary
from globeye.db.models import ScanJob

router = APIRouter(tags=["jobs"], dependencies=[Depends(require_api_key)])


def _job_summary(job: ScanJob) -> JobSummary:
    return JobSummary(
        id=int(job.id or 0),
        case_id=job.case_id,
        target_type=job.target_type,
        target_value=job.target_value,
        pivot=job.pivot,
        status=job.status,
        findings_count=job.findings_count,
        scan_record_id=job.scan_record_id,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.get("/api/cases/{case_id}/jobs")
async def list_case_jobs(
    case_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
    limit: int = 50,
) -> list[JobSummary]:
    await run_in_threadpool(get_case_or_404, engine, case_id)
    limit = min(max(limit, 1), 200)

    def _list() -> list[JobSummary]:
        with Session(engine) as session:
            jobs = list(
                session.exec(
                    select(ScanJob)
                    .where(ScanJob.case_id == case_id)
                    .order_by(ScanJob.id.desc())  # type: ignore[union-attr]
                    .limit(limit)
                ).all()
            )
        return [_job_summary(j) for j in jobs]

    return await run_in_threadpool(_list)


@router.get("/api/jobs/{job_id}")
async def get_job(
    job_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
) -> JobDetail:
    def _get() -> JobDetail:
        with Session(engine) as session:
            job = session.get(ScanJob, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        return JobDetail(
            **_job_summary(job).model_dump(),
            target_raw=job.target_raw,
            error_message=job.error_message,
        )

    return await run_in_threadpool(_get)
