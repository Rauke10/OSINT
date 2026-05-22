"""Per-source scan outcomes for case-bound jobs (Fase 2A)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class SourceResult(SQLModel, table=True):
    """One row per passive source for a scan job."""

    __tablename__ = "source_result"

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    scan_job_id: int = Field(foreign_key="scan_job.id", index=True)
    source_name: str = Field(max_length=64, index=True)
    status: str = Field(max_length=32, index=True)
    findings_count: int = Field(default=0)
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)
    latency_ms: int | None = Field(default=None)
    message: str | None = Field(default=None, max_length=2000)
    error_type: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
