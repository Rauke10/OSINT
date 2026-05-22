"""URL live check API schemas (Fase 2C.2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UrlCheckEntryIn(BaseModel):
    url: str
    entity_id: int | None = None
    evidence_id: int | None = None


class UrlChecksCreateIn(BaseModel):
    urls: list[str] = Field(default_factory=list)
    entries: list[UrlCheckEntryIn] | None = None
    method: str = "HEAD"
    fallback_get: bool = True
    max_urls: int = Field(default=25, ge=1, le=25)


class UrlLiveCheckOut(BaseModel):
    id: int
    case_id: int
    entity_id: int | None = None
    evidence_id: int | None = None
    url: str
    method: str
    status: str
    status_code: int | None = None
    final_url: str | None = None
    content_type: str | None = None
    content_length: int | None = None
    checked_at: datetime | str | None = None
    latency_ms: int | None = None
    error_message: str | None = None
    created_at: datetime | str


class UrlChecksBatchOut(BaseModel):
    checked: int
    results: list[UrlLiveCheckOut]
