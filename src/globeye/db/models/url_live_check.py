"""Optional active URL live checks (Fase 2C.2 — manual, not automatic)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class UrlLiveCheck(SQLModel, table=True):
    """HEAD/GET metadata for a URL checked against the live target (no response body stored)."""

    __tablename__ = "url_live_check"

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    entity_id: int | None = Field(default=None, foreign_key="entity.id", index=True)
    evidence_id: int | None = Field(default=None, foreign_key="evidence.id", index=True)
    url: str = Field(max_length=2048, index=True)
    method: str = Field(default="HEAD", max_length=8)
    status: str = Field(default="not_checked", max_length=32, index=True)
    status_code: int | None = Field(default=None)
    final_url: str | None = Field(default=None, max_length=2048)
    content_type: str | None = Field(default=None, max_length=256)
    content_length: int | None = Field(default=None)
    checked_at: datetime | None = Field(default=None, index=True)
    latency_ms: int | None = Field(default=None)
    error_message: str | None = Field(default=None, max_length=512)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
