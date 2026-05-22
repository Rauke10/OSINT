"""Case quality summary (Fase 2B.1)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.engine import Engine
from starlette.concurrency import run_in_threadpool

from globeye.api.auth import get_engine, require_api_key
from globeye.api.deps import get_case_or_404
from globeye.api.schemas.quality import QualitySummaryOut
from globeye.services.finding_quality import build_case_quality_summary

router = APIRouter(tags=["quality"], dependencies=[Depends(require_api_key)])


@router.get("/api/cases/{case_id}/quality-summary", response_model=QualitySummaryOut)
async def get_case_quality_summary(
    case_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
) -> dict[str, Any]:
    await run_in_threadpool(get_case_or_404, engine, case_id)
    return await run_in_threadpool(build_case_quality_summary, engine, case_id)
