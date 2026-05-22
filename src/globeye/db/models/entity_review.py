"""Manual analyst review, discard, and inventory approval (Fase 2C.3 / 2D)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

INVENTORY_STATUSES = frozenset({"candidate", "approved", "rejected", "needs_review"})
INVENTORY_PRIORITIES = frozenset({"low", "medium", "high", "critical"})


class EntityReview(SQLModel, table=True):
    """Soft-hide or mark entities; inventory approval is manual only."""

    __tablename__ = "entity_review"

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    entity_id: int | None = Field(default=None, foreign_key="entity.id", index=True)
    evidence_id: int | None = Field(default=None, foreign_key="evidence.id", index=True)
    value: str | None = Field(default=None, max_length=2048, index=True)
    review_status: str = Field(default="pending", max_length=32, index=True)
    hidden: bool = Field(default=False, index=True)
    hidden_reason: str | None = Field(default=None, max_length=512)
    note: str | None = Field(default=None, max_length=2000)
    approved_for_inventory: bool = Field(default=False, index=True)
    inventory_status: str = Field(default="candidate", max_length=32, index=True)
    inventory_priority: str | None = Field(default=None, max_length=16, index=True)
    inventory_note: str | None = Field(default=None, max_length=2000)
    approved_at: datetime | None = Field(default=None)
    approved_reason: str | None = Field(default=None, max_length=512)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
