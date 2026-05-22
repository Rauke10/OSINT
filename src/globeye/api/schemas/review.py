"""Entity review and inventory API schemas (Fase 2C.3 / 2D)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EntityReviewPatchIn(BaseModel):
    review_status: str | None = None
    hidden: bool | None = None
    hidden_reason: str | None = None
    note: str | None = None
    approved_for_inventory: bool | None = None
    inventory_status: str | None = None
    inventory_priority: str | None = None
    inventory_note: str | None = None
    approved_reason: str | None = None
    clear_approval: bool = False


class BulkReviewIn(BaseModel):
    entity_ids: list[int] = Field(default_factory=list)
    evidence_ids: list[int] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    action: str | None = Field(
        None,
        description="approve | discard | restore | remove_inventory",
    )
    review_status: str | None = None
    hidden: bool | None = None
    hidden_reason: str | None = None
    note: str | None = None
    approved_for_inventory: bool | None = None
    inventory_status: str | None = None
    inventory_priority: str | None = None
    inventory_note: str | None = None
    approved_reason: str | None = None
    clear_approval: bool = False


class EntityReviewOut(BaseModel):
    id: int
    case_id: int
    entity_id: int | None = None
    evidence_id: int | None = None
    value: str | None = None
    review_status: str
    hidden: bool
    hidden_reason: str | None = None
    note: str | None = None
    approved_for_inventory: bool = False
    inventory_status: str = "candidate"
    inventory_priority: str | None = None
    inventory_note: str | None = None
    approved_at: str | None = None
    approved_reason: str | None = None
    created_at: str
    updated_at: str


class BulkReviewOut(BaseModel):
    updated: int
    reviews: list[EntityReviewOut]
