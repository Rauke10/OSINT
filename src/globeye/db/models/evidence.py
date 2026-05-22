"""Stored evidence artefacts for auditability (Fase 2A)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class StoredEvidence(SQLModel, table=True):
    """Redacted evidence backing a finding or source response."""

    __tablename__ = "evidence"

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    scan_job_id: int = Field(foreign_key="scan_job.id", index=True)
    source_result_id: int | None = Field(default=None, foreign_key="source_result.id", index=True)
    entity_id: int | None = Field(default=None, foreign_key="entity.id", index=True)
    finding_kind: str | None = Field(default=None, max_length=64)
    finding_value: str | None = Field(default=None, max_length=512)
    source_name: str = Field(max_length=64, index=True)
    evidence_type: str = Field(max_length=32, index=True)
    source_url: str | None = Field(default=None, max_length=2048)
    raw_json: str | None = Field(default=None)
    content_hash_sha256: str = Field(max_length=64, index=True)
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sensitive: bool = Field(default=False)
    redacted: bool = Field(default=False)
