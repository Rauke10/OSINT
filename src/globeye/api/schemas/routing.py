"""Source routing preview API schemas (Fase 2B)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from globeye.core.source_profiles import ScanDepth


class SourceRoutingPreviewRequest(BaseModel):
    target: str = Field(min_length=1, max_length=255)
    depth: ScanDepth = ScanDepth.STANDARD
    selected_sources: list[str] | None = None


class RoutedSourceOut(BaseModel):
    source: str
    reason: str
    requires_key: bool
    configured: bool | None = None
    label: str | None = None


class SourceRoutingPreviewResponse(BaseModel):
    target_type: str
    normalized_value: str
    profile: str
    depth: str
    will_run: list[RoutedSourceOut]
    skipped_missing_key: list[RoutedSourceOut]
    not_applicable: list[RoutedSourceOut]
    warnings: list[str] = Field(default_factory=list)
