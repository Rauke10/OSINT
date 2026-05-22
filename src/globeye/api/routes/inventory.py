"""Case inventory (Fase 2D)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.engine import Engine
from starlette.concurrency import run_in_threadpool

from globeye.api.auth import get_engine, require_api_key
from globeye.api.deps import get_case_or_404
from globeye.api.schemas.data import CaseDataOut
from globeye.services.case_inventory import build_case_inventory

router = APIRouter(tags=["inventory"], dependencies=[Depends(require_api_key)])


@router.get("/api/cases/{case_id}/inventory", response_model=CaseDataOut)
async def get_case_inventory(
    case_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
    type_filter: str | None = Query(None, alias="type"),
    source: str | None = Query(None),
    q: str | None = Query(None),
    live_status: str | None = Query(None, alias="live_status"),
    wayback_category: str | None = Query(None),
    wayback_priority: str | None = Query(None),
    inventory_priority: str | None = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    await run_in_threadpool(get_case_or_404, engine, case_id)
    return await run_in_threadpool(
        build_case_inventory,
        engine,
        case_id,
        type_filter=type_filter,
        source_filter=source,
        query=q,
        live_status_filter=live_status,
        wayback_category=wayback_category,
        wayback_priority=wayback_priority,
        inventory_priority=inventory_priority,
        limit=limit,
        offset=offset,
    )
