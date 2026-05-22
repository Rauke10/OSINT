"""Case data explorer API schemas (Fase 2C / 2C.3)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DataExplorerCounts(BaseModel):
    total_count: int = 0
    filtered_count: int = 0
    visible_count: int = 0
    hidden_by_filters_count: int = 0
    hidden_noisy_count: int = 0
    hidden_historical_count: int = 0
    hidden_discarded_count: int = 0
    hidden_false_positive_count: int = 0
    discarded_count: int = 0
    historical_count: int = 0
    noisy_count: int = 0
    false_positive_count: int = 0
    evidence_total_count: int = 0
    evidence_filtered_count: int = 0
    findings_total_count: int = 0
    archived_url_findings_count: int = 0
    url_entity_count: int = 0
    wayback_entity_limit: int = 25
    wayback_live_check_batch_limit: int = 25
    wayback_scan_url_cap: int = 200
    wayback_cdx_fetch_limit: int = 200
    max_api_limit: int = 2000
    wayback_original_total: int = 0
    wayback_evidence_count: int = 0
    wayback_entity_count: int = 0
    wayback_grouped_count: int = 0
    wayback_visible_count: int = 0
    wayback_hidden_by_filters_count: int = 0
    wayback_discarded_count: int = 0
    wayback_live_200_count: int = 0
    wayback_404_count: int = 0
    wayback_pending_live_count: int = 0


class CaseDataItemOut(BaseModel):
    id: int
    type: str
    entity_type: str
    value: str
    display_value: str
    quality_label: str | None = None
    confidence_score: int | None = None
    verification_sources_count: int | None = None
    is_historical: bool = False
    is_potential_false_positive: bool = False
    quality_reason: str | None = None
    sources: list[str] = Field(default_factory=list)
    evidence_count: int = 0
    first_seen_at: str
    last_seen_at: str
    first_job_id: int | None = None
    last_job_id: int | None = None
    is_wayback_url: bool = False
    live_status: str | None = None
    live_checked_at: str | None = None
    last_live_checked_at: str | None = None
    live_status_code: int | None = None
    live_final_url: str | None = None
    live_check_id: int | None = None
    review_status: str = "pending"
    hidden: bool = False
    hidden_reason: str | None = None
    review_note: str | None = None
    wayback_category: str | None = None
    wayback_priority: str | None = None
    wayback_group_key: str | None = None
    operational_status: str | None = None
    normalized_value: str | None = None
    original_values: list[str] = Field(default_factory=list)
    canonical_key: str | None = None
    variant_of: int | None = None
    normalization_reason: str | None = None
    group_key: str | None = None
    group_reason: str | None = None
    evidence_ids: list[int] = Field(default_factory=list)
    source_names: list[str] = Field(default_factory=list)
    approved_for_inventory: bool = False
    inventory_status: str = "candidate"
    inventory_priority: str | None = None
    inventory_note: str | None = None
    approved_at: str | None = None
    approved_reason: str | None = None
    inventory_suggested: bool = False


class CaseDataOut(BaseModel):
    summary: dict[str, int]
    counts: DataExplorerCounts = Field(default_factory=DataExplorerCounts)
    operational_summary: dict[str, int] = Field(default_factory=dict)
    wayback_groups: dict[str, dict[str, int]] = Field(default_factory=dict)
    items: list[CaseDataItemOut]
    total: int
    total_count: int = 0
    visible_count: int = 0
    filtered_count: int = 0
    hidden_by_filters_count: int = 0
    total_filtered: int | None = None
    offset: int
    limit: int
    hidden_noisy_count: int = 0
    hidden_historical_count: int = 0
    hidden_discarded_count: int = 0
    evidence_total_count: int = 0
    evidence_visible_count: int = 0
    findings_total_count: int = 0
