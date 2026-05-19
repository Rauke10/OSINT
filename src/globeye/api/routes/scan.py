"""Scan endpoint: run a passive scan, persist it, return JSON or HTML."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine
from starlette.concurrency import run_in_threadpool

from globeye.api.auth import get_engine, get_settings, require_api_key
from globeye.config import Settings
from globeye.core.db import get_scan, save_scan
from globeye.core.models import ScanResult
from globeye.core.orchestrator import Orchestrator
from globeye.core.target import TargetDetectionError, detect
from globeye.report.html_writer import to_html
from globeye.report.json_writer import to_dict

router = APIRouter(tags=["scan"], dependencies=[Depends(require_api_key)])


class ScanRequest(BaseModel):
    target: str = Field(min_length=1, max_length=255)
    pivot: bool = False


@router.post("/api/scan")
async def run_scan(
    body: ScanRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[Engine, Depends(get_engine)],
) -> dict[str, Any]:
    try:
        target = detect(body.target)
    except TargetDetectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"invalid target: {exc}",
        ) from exc

    result = await Orchestrator(settings).scan(target, pivot=body.pivot)
    scan_id = await run_in_threadpool(save_scan, engine, result)
    payload = to_dict(result)
    payload["scan_id"] = scan_id
    return payload


@router.get("/api/scan/{scan_id}/report", response_class=HTMLResponse)
async def scan_report(
    scan_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
) -> HTMLResponse:
    record = await run_in_threadpool(get_scan, engine, scan_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    result = ScanResult.model_validate_json(record.model_json)
    return HTMLResponse(to_html(result))
