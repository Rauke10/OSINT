"""Quality summary API schemas (Fase 2B.1)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EntityOutQuality(BaseModel):
    quality_label: str | None = None
    confidence_score: int | None = Field(default=None, ge=0, le=100)
    verification_sources_count: int | None = None
    is_historical: bool = False
    is_potential_false_positive: bool = False
    quality_reason: str | None = None


class QualitySummaryOut(BaseModel):
    case_id: int
    total_entities: int
    total_findings: int
    entities_by_label: dict[str, int]
    findings_by_label: dict[str, int]
    top_sources_verified: list[tuple[str, int]]
    top_sources_noise: list[tuple[str, int]]
