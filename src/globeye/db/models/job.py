"""Scan job tracking for case-bound scans."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class ScanJob(SQLModel, table=True):
    """One passive scan run within a case."""

    __tablename__ = "scan_job"

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    target_raw: str = Field(max_length=512)
    target_type: str = Field(max_length=32)
    target_value: str = Field(max_length=255, index=True)
    pivot: bool = Field(default=False)
    status: str = Field(default="pending", max_length=32, index=True)
    scan_record_id: int | None = Field(default=None, index=True)
    error_message: str | None = Field(default=None, max_length=2000)
    findings_count: int = Field(default=0)
    owner_id: str | None = Field(default=None, max_length=128)  # FUTURE: User FK
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = Field(default=None)
