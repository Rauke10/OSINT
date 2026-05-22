"""Case and case target tables."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class Case(SQLModel, table=True):
    """An OSINT investigation workspace."""

    __tablename__ = "case"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=200, index=True)
    description: str | None = Field(default=None, max_length=4000)
    status: str = Field(default="open", max_length=32, index=True)
    reference_code: str | None = Field(default=None, max_length=64)
    owner_id: str | None = Field(default=None, max_length=128)  # FUTURE: User FK
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CaseTarget(SQLModel, table=True):
    """A target associated with a case (optional seed before scanning)."""

    __tablename__ = "case_target"
    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "target_type",
            "normalized_value",
            name="uq_case_target",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    raw_input: str = Field(max_length=512)
    target_type: str = Field(max_length=32)
    normalized_value: str = Field(max_length=255, index=True)
    is_primary: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
