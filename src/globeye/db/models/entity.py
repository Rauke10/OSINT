"""Entity graph tables per case."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class Entity(SQLModel, table=True):
    """A normalized entity discovered within a case."""

    __tablename__ = "entity"
    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "entity_type",
            "normalized_value",
            name="uq_entity",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    entity_type: str = Field(max_length=64, index=True)
    normalized_value: str = Field(max_length=512)
    display_value: str = Field(max_length=512)
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_job_id: int | None = Field(default=None, foreign_key="scan_job.id")


class EntityRelationship(SQLModel, table=True):
    """A directed relationship between two entities in a case."""

    __tablename__ = "entity_relationship"
    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            "source_name",
            name="uq_entity_relationship",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    source_entity_id: int = Field(foreign_key="entity.id", index=True)
    target_entity_id: int = Field(foreign_key="entity.id", index=True)
    relationship_type: str = Field(max_length=64)
    source_name: str = Field(max_length=64)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
