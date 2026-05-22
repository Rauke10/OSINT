"""Health & metadata endpoints (no auth)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from globeye import __version__
from globeye.api.auth import get_settings
from globeye.config import Settings
from globeye.services.source_diagnostics import enrich_status_row
from globeye.services.source_status import describe_source_status
from globeye.sources.base import discover_sources
from globeye.sources.catalog import describe_sources

router = APIRouter(tags=["meta"])


@router.get("/api/health")
async def health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "sources": sorted(cls.name for cls in discover_sources()),
        "api_debug": settings.api_debug,
    }


@router.get("/api/sources")
async def sources(
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, Any]]:
    """Catalogue of every passive source: label, what it indexes, availability."""
    return describe_sources(settings)


@router.get("/api/sources/status")
async def sources_status(
    settings: Annotated[Settings, Depends(get_settings)],
    check: bool = False,
) -> list[dict[str, Any]]:
    """Per-source configuration and optional light probe (no secrets returned)."""
    rows = await describe_source_status(settings, probe=check)
    return [enrich_status_row(r, settings) for r in rows]
