"""Case and case-target endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.engine import Engine
from sqlmodel import Session, select
from starlette.concurrency import run_in_threadpool

from globeye.api.auth import get_engine, get_settings, require_api_key
from globeye.api.deps import case_counts, get_case_or_404
from globeye.api.schemas.cases import (
    CaseCreate,
    CaseOut,
    CaseScanRequest,
    CaseTargetCreate,
    CaseTargetOut,
    CaseUpdate,
)
from globeye.config import Settings
from globeye.core.target import TargetDetectionError, detect
from globeye.db.models import Case, CaseTarget
from globeye.services.case_delete import delete_case
from globeye.services.entity_normalizer import build_case_graph
from globeye.services.scan_service import run_case_scan

router = APIRouter(tags=["cases"], dependencies=[Depends(require_api_key)])


def _case_out(case: Case, *, counts: tuple[int, int, int] | None = None) -> CaseOut:
    tc, jc, ec = counts if counts is not None else (None, None, None)
    return CaseOut(
        id=int(case.id or 0),
        title=case.title,
        description=case.description,
        status=case.status,
        reference_code=case.reference_code,
        created_at=case.created_at,
        updated_at=case.updated_at,
        targets_count=tc,
        jobs_count=jc,
        entities_count=ec,
    )


@router.post("/api/cases", status_code=status.HTTP_201_CREATED)
async def create_case(
    body: CaseCreate,
    engine: Annotated[Engine, Depends(get_engine)],
) -> CaseOut:
    now = datetime.now(UTC)
    case = Case(
        title=body.title,
        description=body.description,
        reference_code=body.reference_code,
        status="open",
        created_at=now,
        updated_at=now,
    )

    def _save() -> Case:
        with Session(engine) as session:
            session.add(case)
            session.commit()
            session.refresh(case)
        return case

    saved = await run_in_threadpool(_save)
    return _case_out(saved, counts=(0, 0, 0))


@router.get("/api/cases")
async def list_cases(
    engine: Annotated[Engine, Depends(get_engine)],
    status_filter: str | None = None,
    include_archived: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[CaseOut]:
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)

    def _list() -> list[CaseOut]:
        with Session(engine) as session:
            stmt = select(Case).order_by(Case.id.desc())  # type: ignore[union-attr]
            if status_filter:
                stmt = stmt.where(Case.status == status_filter)
            elif not include_archived:
                stmt = stmt.where(Case.status != "archived")
            stmt = stmt.offset(offset).limit(limit)
            cases = list(session.exec(stmt).all())
        return [_case_out(c, counts=case_counts(engine, int(c.id or 0))) for c in cases]

    return await run_in_threadpool(_list)


@router.get("/api/cases/{case_id}")
async def get_case(
    case_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
) -> CaseOut:
    case = await run_in_threadpool(get_case_or_404, engine, case_id)
    counts = await run_in_threadpool(case_counts, engine, case_id)
    return _case_out(case, counts=counts)


@router.patch("/api/cases/{case_id}")
async def update_case(
    case_id: int,
    body: CaseUpdate,
    engine: Annotated[Engine, Depends(get_engine)],
) -> CaseOut:
    await run_in_threadpool(get_case_or_404, engine, case_id)

    def _patch() -> Case:
        with Session(engine) as session:
            case = session.get(Case, case_id)
            if case is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="case not found")
            if body.title is not None:
                case.title = body.title
            if body.description is not None:
                case.description = body.description
            if body.status is not None:
                if body.status not in {"open", "archived"}:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="status must be open or archived",
                    )
                case.status = body.status
            case.updated_at = datetime.now(UTC)
            session.add(case)
            session.commit()
            session.refresh(case)
            return case

    case = await run_in_threadpool(_patch)
    counts = await run_in_threadpool(case_counts, engine, case_id)
    return _case_out(case, counts=counts)


@router.post("/api/cases/{case_id}/targets", status_code=status.HTTP_201_CREATED)
async def add_case_target(
    case_id: int,
    body: CaseTargetCreate,
    engine: Annotated[Engine, Depends(get_engine)],
) -> CaseTargetOut:
    await run_in_threadpool(get_case_or_404, engine, case_id)
    try:
        target = detect(body.target)
    except TargetDetectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"invalid target: {exc}",
        ) from exc

    def _add() -> CaseTarget:
        with Session(engine) as session:
            existing = session.exec(
                select(CaseTarget).where(
                    CaseTarget.case_id == case_id,
                    CaseTarget.target_type == target.type.value,
                    CaseTarget.normalized_value == target.value,
                )
            ).first()
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="target already exists for this case",
                )
            row = CaseTarget(
                case_id=case_id,
                raw_input=body.target.strip(),
                target_type=target.type.value,
                normalized_value=target.value,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    try:
        row = await run_in_threadpool(_add)
    except HTTPException:
        raise
    return CaseTargetOut(
        id=int(row.id or 0),
        case_id=row.case_id,
        raw_input=row.raw_input,
        target_type=row.target_type,
        normalized_value=row.normalized_value,
        is_primary=row.is_primary,
        created_at=row.created_at,
    )


@router.get("/api/cases/{case_id}/targets")
async def list_case_targets(
    case_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
) -> list[CaseTargetOut]:
    await run_in_threadpool(get_case_or_404, engine, case_id)

    def _list() -> list[CaseTargetOut]:
        with Session(engine) as session:
            rows = list(
                session.exec(
                    select(CaseTarget)
                    .where(CaseTarget.case_id == case_id)
                    .order_by(CaseTarget.id.desc())  # type: ignore[union-attr]
                ).all()
            )
        return [
            CaseTargetOut(
                id=int(r.id or 0),
                case_id=r.case_id,
                raw_input=r.raw_input,
                target_type=r.target_type,
                normalized_value=r.normalized_value,
                is_primary=r.is_primary,
                created_at=r.created_at,
            )
            for r in rows
        ]

    return await run_in_threadpool(_list)


@router.post("/api/cases/{case_id}/scans")
async def run_case_scan_endpoint(
    case_id: int,
    body: CaseScanRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[Engine, Depends(get_engine)],
) -> dict[str, Any]:
    await run_in_threadpool(get_case_or_404, engine, case_id)
    try:
        target = detect(body.target)
    except TargetDetectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"invalid target: {exc}",
        ) from exc

    return await run_case_scan(
        engine,
        settings,
        case_id=case_id,
        target=target,
        pivot=body.pivot,
        depth=body.depth,
        selected_sources=body.selected_sources,
    )


@router.delete("/api/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_case(
    case_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
) -> None:
    await run_in_threadpool(get_case_or_404, engine, case_id)
    await run_in_threadpool(delete_case, engine, case_id)


@router.get("/api/cases/{case_id}/graph")
async def get_case_graph(
    case_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
    mode: str = Query("inventory", description="inventory|all|live|high"),
) -> dict[str, Any]:
    await run_in_threadpool(get_case_or_404, engine, case_id)
    if mode not in {"inventory", "all", "live", "high"}:
        mode = "inventory"
    return await run_in_threadpool(build_case_graph, engine, case_id, mode=mode)
