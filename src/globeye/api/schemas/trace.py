"""Entity trace API schemas (Fase 2C.4)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TraceGroupOut(BaseModel):
    key: str | None = None
    category: str | None = None
    priority: str | None = None
    reason: str | None = None
    non_destructive: bool = True


class TraceNormalizationOut(BaseModel):
    reason: str = ""
    canonical_key: str | None = None
    variant_of: int | None = None
    merge_policy: str = "distinct"
    is_normalized_variant: bool = False


class TraceQualityOut(BaseModel):
    label: str | None = None
    reason: str | None = None


class TraceReviewOut(BaseModel):
    review_status: str = "pending"
    hidden: bool = False
    hidden_reason: str | None = None
    note: str | None = None


class EntityTraceOut(BaseModel):
    entity_id: int
    case_id: int
    entity_type: str
    display_value: str
    normalized_value: str
    original_values: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    source_names: list[str] = Field(default_factory=list)
    evidence_ids: list[int] = Field(default_factory=list)
    evidence_count: int = 0
    findings: list[dict[str, Any]] = Field(default_factory=list)
    group: TraceGroupOut | None = None
    normalization: TraceNormalizationOut = Field(default_factory=TraceNormalizationOut)
    quality: TraceQualityOut | None = None
    live_check: dict[str, Any] | None = None
    review: TraceReviewOut = Field(default_factory=TraceReviewOut)
