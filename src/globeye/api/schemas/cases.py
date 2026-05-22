"""Case, job, and entity API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from globeye.core.source_profiles import ScanDepth


class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    reference_code: str | None = Field(default=None, max_length=64)


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    status: str | None = Field(default=None, max_length=32)


class CaseOut(BaseModel):
    id: int
    title: str
    description: str | None
    status: str
    reference_code: str | None
    created_at: datetime
    updated_at: datetime
    targets_count: int | None = None
    jobs_count: int | None = None
    entities_count: int | None = None


class CaseTargetCreate(BaseModel):
    target: str = Field(min_length=1, max_length=255)


class CaseTargetOut(BaseModel):
    id: int
    case_id: int
    raw_input: str
    target_type: str
    normalized_value: str
    is_primary: bool
    created_at: datetime


class CaseScanRequest(BaseModel):
    target: str = Field(min_length=1, max_length=255)
    pivot: bool = False
    depth: ScanDepth = ScanDepth.STANDARD
    selected_sources: list[str] | None = None


class JobSummary(BaseModel):
    id: int
    case_id: int
    target_type: str
    target_value: str
    pivot: bool
    status: str
    findings_count: int
    scan_record_id: int | None
    started_at: datetime
    finished_at: datetime | None


class JobDetail(JobSummary):
    target_raw: str
    error_message: str | None


class EntityOut(BaseModel):
    id: int
    case_id: int
    entity_type: str
    normalized_value: str
    display_value: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_job_id: int | None
    quality_label: str | None = None
    confidence_score: int | None = None
    verification_sources_count: int | None = None
    is_historical: bool = False
    is_potential_false_positive: bool = False
    quality_reason: str | None = None


class RelationshipEdge(BaseModel):
    id: int
    relationship_type: str
    source_name: str
    peer_entity_id: int
    peer_entity_type: str
    peer_display_value: str
    direction: str


class EntityRelationshipsOut(BaseModel):
    entity_id: int
    outgoing: list[RelationshipEdge]
    incoming: list[RelationshipEdge]
