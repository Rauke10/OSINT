"""API schemas for source results and stored evidence (Fase 2A)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SourceResultOut(BaseModel):
    id: int
    case_id: int
    scan_job_id: int
    source_name: str
    status: str
    findings_count: int
    started_at: datetime | None
    finished_at: datetime | None
    latency_ms: int | None
    message: str | None
    error_type: str | None
    created_at: datetime


class UrlLiveCheckBrief(BaseModel):
    id: int
    status: str
    status_code: int | None = None
    final_url: str | None = None
    content_type: str | None = None
    content_length: int | None = None
    checked_at: datetime | str | None = None
    latency_ms: int | None = None
    method: str | None = None
    error_message: str | None = None


class EvidenceSummary(BaseModel):
    id: int
    case_id: int
    scan_job_id: int
    source_result_id: int | None
    entity_id: int | None
    finding_kind: str | None
    finding_value: str | None
    source_name: str
    evidence_type: str
    source_url: str | None
    content_hash_sha256: str
    hash_short: str = Field(description="Last 8 hex chars of SHA-256")
    collected_at: datetime
    sensitive: bool
    redacted: bool
    live_check: UrlLiveCheckBrief | None = None


class EvidenceDetail(EvidenceSummary):
    raw_json: str | None = None
    created_at: datetime


class EvidenceHashOut(BaseModel):
    evidence_id: int
    algorithm: str = "sha256"
    content_hash_sha256: str
