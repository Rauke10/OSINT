"""Health & metadata endpoints (no auth)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from globeye import __version__
from globeye.api.auth import get_settings
from globeye.config import Settings
from globeye.sources.base import discover_sources
from globeye.sources.catalog import describe_sources

router = APIRouter(tags=["meta"])


@router.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "sources": sorted(cls.name for cls in discover_sources()),
    }


@router.get("/api/sources")
async def sources(
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, Any]]:
    """Catalogue of every passive source: label, what it indexes, availability."""
    return describe_sources(settings)
