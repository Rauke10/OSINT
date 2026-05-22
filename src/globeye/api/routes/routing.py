"""Source routing preview (Fase 2B)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from globeye.api.schemas.routing import (
    SourceRoutingPreviewRequest,
    SourceRoutingPreviewResponse,
)
from globeye.config import Settings, get_settings
from globeye.core.target import TargetDetectionError, detect
from globeye.services.source_router import plan_routing

router = APIRouter(tags=["routing"])


@router.post("/api/source-routing/preview", response_model=SourceRoutingPreviewResponse)
async def preview_source_routing(
    body: SourceRoutingPreviewRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SourceRoutingPreviewResponse:
    """Preview which passive sources would run for a target and depth."""
    try:
        target = detect(body.target)
    except TargetDetectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"invalid target: {exc}",
        ) from exc

    plan = plan_routing(
        settings,
        target,
        depth=body.depth,
        selected_sources=body.selected_sources,
    )
    preview = plan.to_preview_dict()
    return SourceRoutingPreviewResponse.model_validate(preview)
