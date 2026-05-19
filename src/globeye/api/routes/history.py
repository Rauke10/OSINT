"""Scan history endpoints (SQLite-backed)."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Engine
from starlette.concurrency import run_in_threadpool

from globeye.api.auth import get_engine, require_api_key
from globeye.core.db import get_scan, list_scans

router = APIRouter(tags=["history"], dependencies=[Depends(require_api_key)])


@router.get("/api/history")
async def history(
    engine: Annotated[Engine, Depends(get_engine)],
    limit: int = 50,
) -> list[dict[str, Any]]:
    records = await run_in_threadpool(list_scans, engine, min(max(limit, 1), 200))
    return [
        {
            "id": r.id,
            "target_value": r.target_value,
            "target_type": r.target_type,
            "created_at": r.created_at.isoformat(),
            "total_findings": r.total_findings,
            "summary": json.loads(r.summary_json),
        }
        for r in records
    ]


@router.get("/api/history/{scan_id}")
async def history_item(
    scan_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
) -> dict[str, Any]:
    record = await run_in_threadpool(get_scan, engine, scan_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    result: dict[str, Any] = json.loads(record.result_json)
    return result
