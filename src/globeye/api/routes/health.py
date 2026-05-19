"""Health & metadata endpoint (no auth)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from globeye import __version__
from globeye.sources.base import discover_sources

router = APIRouter(tags=["meta"])


@router.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "sources": sorted(cls.name for cls in discover_sources()),
    }
