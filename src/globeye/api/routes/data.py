"""Case data explorer (Fase 2C / 2C.3)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.engine import Engine
from starlette.concurrency import run_in_threadpool

from globeye.api.auth import get_engine, require_api_key
from globeye.api.deps import get_case_or_404
from globeye.api.schemas.data import CaseDataOut
from globeye.services.case_data import build_case_data

router = APIRouter(tags=["data"], dependencies=[Depends(require_api_key)])


@router.get("/api/cases/{case_id}/data", response_model=CaseDataOut)
async def get_case_data(
    case_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
    type_filter: str | None = Query(None, alias="type"),
    quality: str | None = Query(None, alias="quality"),
    source: str | None = Query(None),
    q: str | None = Query(None),
    hide_noisy: bool = Query(False),
    hide_historical: bool = Query(False),
    hide_false_positive: bool = Query(False),
    verified_only: bool = Query(False),
    live_status: str | None = Query(None, alias="live_status"),
    hide_discarded: bool = Query(False),
    review_status: str | None = Query(None),
    wayback_category: str | None = Query(None),
    wayback_priority: str | None = Query(None),
    operational_status: str | None = Query(None),
    only_high_priority: bool = Query(False),
    inventory_status: str | None = Query("pending", alias="inventory_status"),
    debug_timing: bool = Query(False),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Aggregated case data for the Data Explorer UI."""
    await run_in_threadpool(get_case_or_404, engine, case_id)
    return await run_in_threadpool(
        build_case_data,
        engine,
        case_id,
        type_filter=type_filter,
        quality_filter=quality,
        source_filter=source,
        query=q,
        hide_noisy=hide_noisy,
        hide_historical=hide_historical,
        hide_false_positive=hide_false_positive,
        verified_only=verified_only,
        live_status_filter=live_status,
        hide_discarded=hide_discarded,
        review_status_filter=review_status,
        wayback_category=wayback_category,
        wayback_priority=wayback_priority,
        operational_status_filter=operational_status,
        only_high_priority=only_high_priority,
        inventory_status_filter=inventory_status,
        limit=limit,
        offset=offset,
        debug_timing=debug_timing,
    )
