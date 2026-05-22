"""Source results and evidence endpoints (Fase 2A)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Engine
from sqlmodel import Session, select
from starlette.concurrency import run_in_threadpool

from globeye.api.auth import get_engine, require_api_key
from globeye.api.deps import get_case_or_404
from globeye.api.schemas.evidence import (
    EvidenceDetail,
    EvidenceHashOut,
    EvidenceSummary,
    SourceResultOut,
    UrlLiveCheckBrief,
)
from globeye.db.models import ScanJob, SourceResult, StoredEvidence
from globeye.services.url_live_check import latest_check_for_evidence

router = APIRouter(tags=["evidence"], dependencies=[Depends(require_api_key)])


def _hash_short(digest: str) -> str:
    return digest[-8:] if len(digest) >= 8 else digest


def _source_result_out(row: SourceResult) -> SourceResultOut:
    return SourceResultOut(
        id=int(row.id or 0),
        case_id=row.case_id,
        scan_job_id=row.scan_job_id,
        source_name=row.source_name,
        status=row.status,
        findings_count=row.findings_count,
        started_at=row.started_at,
        finished_at=row.finished_at,
        latency_ms=row.latency_ms,
        message=row.message,
        error_type=row.error_type,
        created_at=row.created_at,
    )


def _live_check_brief(engine: Engine, row: StoredEvidence) -> UrlLiveCheckBrief | None:
    if row.source_name != "wayback" and row.finding_kind not in {"archived_url", "url"}:
        return None
    live = latest_check_for_evidence(
        engine,
        row.case_id,
        entity_id=row.entity_id,
        evidence_id=int(row.id or 0),
    )
    if live is None:
        return None
    return UrlLiveCheckBrief(
        id=int(live["id"]),
        status=str(live["status"]),
        status_code=live.get("status_code"),
        final_url=live.get("final_url"),
        content_type=live.get("content_type"),
        content_length=live.get("content_length"),
        checked_at=live.get("checked_at"),
        latency_ms=live.get("latency_ms"),
        method=live.get("method"),
        error_message=live.get("error_message"),
    )


def _evidence_summary(engine: Engine, row: StoredEvidence) -> EvidenceSummary:
    digest = row.content_hash_sha256
    return EvidenceSummary(
        id=int(row.id or 0),
        case_id=row.case_id,
        scan_job_id=row.scan_job_id,
        source_result_id=row.source_result_id,
        entity_id=row.entity_id,
        finding_kind=row.finding_kind,
        finding_value=row.finding_value,
        source_name=row.source_name,
        evidence_type=row.evidence_type,
        source_url=row.source_url,
        content_hash_sha256=digest,
        hash_short=_hash_short(digest),
        collected_at=row.collected_at,
        sensitive=row.sensitive,
        redacted=row.redacted,
        live_check=_live_check_brief(engine, row),
    )


def _evidence_detail(engine: Engine, row: StoredEvidence) -> EvidenceDetail:
    base = _evidence_summary(engine, row)
    return EvidenceDetail(
        **base.model_dump(),
        raw_json=row.raw_json,
        created_at=row.created_at,
    )


def _list_source_results(
    engine: Engine,
    *,
    case_id: int | None = None,
    job_id: int | None = None,
    status_filter: str | None = None,
    source_name: str | None = None,
) -> list[SourceResultOut]:
    with Session(engine) as session:
        stmt = select(SourceResult)
        if case_id is not None:
            stmt = stmt.where(SourceResult.case_id == case_id)
        if job_id is not None:
            stmt = stmt.where(SourceResult.scan_job_id == job_id)
        if status_filter:
            stmt = stmt.where(SourceResult.status == status_filter)
        if source_name:
            stmt = stmt.where(SourceResult.source_name == source_name)
        stmt = stmt.order_by(SourceResult.id.desc())  # type: ignore[union-attr]
        rows = list(session.exec(stmt).all())
    return [_source_result_out(r) for r in rows]


def _list_evidence(
    engine: Engine,
    *,
    case_id: int | None = None,
    job_id: int | None = None,
    source_name: str | None = None,
    entity_id: int | None = None,
) -> list[EvidenceSummary]:
    with Session(engine) as session:
        stmt = select(StoredEvidence)
        if case_id is not None:
            stmt = stmt.where(StoredEvidence.case_id == case_id)
        if job_id is not None:
            stmt = stmt.where(StoredEvidence.scan_job_id == job_id)
        if source_name:
            stmt = stmt.where(StoredEvidence.source_name == source_name)
        if entity_id is not None:
            stmt = stmt.where(StoredEvidence.entity_id == entity_id)
        stmt = stmt.order_by(StoredEvidence.id.desc())  # type: ignore[union-attr]
        rows = list(session.exec(stmt).all())
    return [_evidence_summary(engine, r) for r in rows]


@router.get("/api/cases/{case_id}/sources")
async def list_case_sources(
    case_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
    job_id: int | None = None,
    status_filter: str | None = None,
    source_name: str | None = None,
) -> list[SourceResultOut]:
    await run_in_threadpool(get_case_or_404, engine, case_id)
    return await run_in_threadpool(
        _list_source_results,
        engine,
        case_id=case_id,
        job_id=job_id,
        status_filter=status_filter,
        source_name=source_name,
    )


@router.get("/api/cases/{case_id}/evidence")
async def list_case_evidence(
    case_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
    job_id: int | None = None,
    source_name: str | None = None,
    entity_id: int | None = None,
) -> list[EvidenceSummary]:
    await run_in_threadpool(get_case_or_404, engine, case_id)
    return await run_in_threadpool(
        _list_evidence,
        engine,
        case_id=case_id,
        job_id=job_id,
        source_name=source_name,
        entity_id=entity_id,
    )


@router.get("/api/jobs/{job_id}/sources")
async def list_job_sources(
    job_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
    status_filter: str | None = None,
    source_name: str | None = None,
) -> list[SourceResultOut]:
    def _check() -> int:
        with Session(engine) as session:
            job = session.get(ScanJob, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        return job.case_id

    case_id = await run_in_threadpool(_check)
    return await run_in_threadpool(
        _list_source_results,
        engine,
        case_id=case_id,
        job_id=job_id,
        status_filter=status_filter,
        source_name=source_name,
    )


@router.get("/api/jobs/{job_id}/evidence")
async def list_job_evidence(
    job_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
    source_name: str | None = None,
    entity_id: int | None = None,
) -> list[EvidenceSummary]:
    def _check() -> int:
        with Session(engine) as session:
            job = session.get(ScanJob, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        return job.case_id

    case_id = await run_in_threadpool(_check)
    return await run_in_threadpool(
        _list_evidence,
        engine,
        case_id=case_id,
        job_id=job_id,
        source_name=source_name,
        entity_id=entity_id,
    )


@router.get("/api/evidence/{evidence_id}")
async def get_evidence(
    evidence_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
) -> EvidenceDetail:
    def _get() -> EvidenceDetail:
        with Session(engine) as session:
            row = session.get(StoredEvidence, evidence_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="evidence not found")
        return _evidence_detail(engine, row)

    return await run_in_threadpool(_get)


@router.get("/api/evidence/{evidence_id}/hash")
async def get_evidence_hash(
    evidence_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
) -> EvidenceHashOut:
    def _get() -> EvidenceHashOut:
        with Session(engine) as session:
            row = session.get(StoredEvidence, evidence_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="evidence not found")
        return EvidenceHashOut(
            evidence_id=int(row.id or 0),
            content_hash_sha256=row.content_hash_sha256,
        )

    return await run_in_threadpool(_get)
