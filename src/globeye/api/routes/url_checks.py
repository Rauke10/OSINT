"""Manual URL live checks (Fase 2C.2)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.engine import Engine
from starlette.concurrency import run_in_threadpool

from globeye.api.auth import get_engine, get_settings, require_api_key
from globeye.api.deps import get_case_or_404
from globeye.api.schemas.url_checks import UrlChecksBatchOut, UrlChecksCreateIn, UrlLiveCheckOut
from globeye.config import Settings
from globeye.services.url_live_check import (
    MAX_BATCH_URLS,
    get_url_check,
    list_url_checks,
    run_url_checks,
)

router = APIRouter(tags=["url-checks"], dependencies=[Depends(require_api_key)])


def _entries_from_body(body: UrlChecksCreateIn) -> list[dict[str, Any]]:
    if body.entries:
        return [
            {
                "url": e.url,
                "entity_id": e.entity_id,
                "evidence_id": e.evidence_id,
            }
            for e in body.entries
        ]
    return [{"url": u, "entity_id": None, "evidence_id": None} for u in body.urls]


@router.post(
    "/api/cases/{case_id}/url-checks",
    response_model=UrlChecksBatchOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_url_checks(
    case_id: int,
    body: UrlChecksCreateIn,
    engine: Annotated[Engine, Depends(get_engine)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    """Run manual live checks for up to 25 URLs (contacts target servers)."""
    await run_in_threadpool(get_case_or_404, engine, case_id)
    entries = _entries_from_body(body)
    if not entries:
        raise HTTPException(status_code=400, detail="Provide urls or entries")
    cap = min(body.max_urls, MAX_BATCH_URLS)
    return await run_url_checks(
        engine,
        settings,
        case_id,
        entries,
        method=body.method,
        fallback_get=body.fallback_get,
        max_urls=cap,
    )


@router.get("/api/cases/{case_id}/url-checks", response_model=list[UrlLiveCheckOut])
async def list_case_url_checks(
    case_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
    status_filter: str | None = Query(None, alias="status"),
    entity_id: int | None = Query(None),
    evidence_id: int | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    await run_in_threadpool(get_case_or_404, engine, case_id)
    return await run_in_threadpool(
        list_url_checks,
        engine,
        case_id,
        status_filter=status_filter,
        entity_id=entity_id,
        evidence_id=evidence_id,
        query=q,
        limit=limit,
        offset=offset,
    )


@router.get("/api/url-checks/{check_id}", response_model=UrlLiveCheckOut)
async def get_url_check_by_id(
    check_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
) -> dict[str, Any]:
    row = await run_in_threadpool(get_url_check, engine, check_id)
    if row is None:
        raise HTTPException(status_code=404, detail="URL check not found")
    return row
