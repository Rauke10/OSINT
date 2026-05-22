export type Confidence = "low" | "medium" | "high";

export interface TargetRef {
  raw: string;
  type: string;
  value: string;
}

export interface GraphNodeHint {
  node_type: string;
  node_id: string;
  label: string;
  parent_id: string | null;
}

export interface FindingQuality {
  quality_label: string;
  confidence_score: number;
  verification_sources_count?: number;
  is_historical?: boolean;
  is_potential_false_positive?: boolean;
  quality_reason?: string;
}

export interface Finding {
  source: string;
  target: string;
  timestamp: string;
  confidence: Confidence;
  kind: string;
  value: string;
  normalized_data: Record<string, unknown> & { quality?: FindingQuality };
  graph_node_hint: GraphNodeHint | null;
  pivot_target: TargetRef | null;
}

export interface ScanSummary {
  duration_seconds: number;
  sources_used: string[];
  sources_skipped: Record<string, string>;
  findings: { low: number; medium: number; high: number; total: number };
  pivoted_targets: TargetRef[];
}

export type ScanDepth = "quick" | "standard" | "deep";

export interface RoutedSourceEntry {
  source: string;
  reason: string;
  requires_key: boolean;
  configured?: boolean;
  label?: string;
}

export interface SourceRoutingPreview {
  target_type: string;
  normalized_value: string;
  profile: string;
  depth: string;
  will_run: RoutedSourceEntry[];
  skipped_missing_key: RoutedSourceEntry[];
  skipped_by_depth?: RoutedSourceEntry[];
  disabled?: RoutedSourceEntry[];
  not_applicable: RoutedSourceEntry[];
  warnings: string[];
}

export interface SourceStatusRow {
  name: string;
  label?: string;
  status: string;
  credential_status?: string;
  probe_scan_status?: string | null;
  ui_category?: string;
  message?: string;
  http_status?: number | null;
  provider_error_code?: string | null;
  provider_error_message_sanitized?: string | null;
  checked_endpoint_name?: string | null;
  auth_method?: string | null;
  checked_at?: string | null;
  fix_hint?: string | null;
  how_to_fix?: string | null;
  env_vars?: string[];
  masked_hint?: string | null;
  configured?: boolean;
  requires_api_key?: boolean;
}

export interface ScanResult {
  scan_id?: number;
  job_id?: number;
  case_id?: number;
  target: TargetRef;
  summary: ScanSummary;
  findings: Finding[];
  routing?: SourceRoutingPreview;
}

export interface HistoryItem {
  id: number;
  target_value: string;
  target_type: string;
  created_at: string;
  total_findings: number;
}

export interface SourceInfo {
  name: string;
  label: string;
  description: string;
  requires_api_key: boolean;
  configured?: boolean;
  available: boolean;
  targets: string[];
}

export interface Case {
  id: number;
  title: string;
  description: string | null;
  status: string;
  reference_code: string | null;
  created_at: string;
  updated_at: string;
  targets_count?: number;
  jobs_count?: number;
  entities_count?: number;
}

export interface CaseCreate {
  title: string;
  description?: string;
}

export type QualityLabel =
  | "verified"
  | "likely"
  | "historical"
  | "unverified"
  | "noisy"
  | "possible_false_positive";

export interface Entity {
  id: number;
  case_id: number;
  entity_type: string;
  normalized_value: string;
  display_value: string;
  first_seen_at: string;
  last_seen_at: string;
  last_job_id: number | null;
  quality_label?: QualityLabel | string | null;
  confidence_score?: number | null;
  verification_sources_count?: number | null;
  is_historical?: boolean;
  is_potential_false_positive?: boolean;
  quality_reason?: string | null;
}

export type UrlLiveStatus =
  | "not_checked"
  | "live_200"
  | "redirect"
  | "forbidden"
  | "not_found"
  | "server_error"
  | "timeout"
  | "network_error"
  | "invalid_url";

export interface UrlLiveCheckBrief {
  id: number;
  status: UrlLiveStatus | string;
  status_code?: number | null;
  final_url?: string | null;
  content_type?: string | null;
  content_length?: number | null;
  checked_at?: string | null;
  latency_ms?: number | null;
  method?: string | null;
  error_message?: string | null;
}

export interface UrlLiveCheckResult extends UrlLiveCheckBrief {
  case_id: number;
  entity_id: number | null;
  evidence_id: number | null;
  url: string;
  created_at: string;
}

export interface CaseDataItem {
  id: number;
  type: string;
  entity_type: string;
  value: string;
  display_value: string;
  quality_label?: string | null;
  confidence_score?: number | null;
  verification_sources_count?: number | null;
  is_historical?: boolean;
  is_potential_false_positive?: boolean;
  quality_reason?: string | null;
  sources: string[];
  evidence_count: number;
  first_seen_at: string;
  last_seen_at: string;
  first_job_id: number | null;
  last_job_id: number | null;
  is_wayback_url?: boolean;
  live_status?: UrlLiveStatus | string | null;
  live_checked_at?: string | null;
  live_status_code?: number | null;
  live_final_url?: string | null;
  live_check_id?: number | null;
  review_status?: string;
  hidden?: boolean;
  hidden_reason?: string | null;
  review_note?: string | null;
  wayback_category?: string | null;
  wayback_priority?: string | null;
  wayback_group_key?: string | null;
  operational_status?: string | null;
  last_live_checked_at?: string | null;
  normalized_value?: string | null;
  original_values?: string[];
  canonical_key?: string | null;
  variant_of?: number | null;
  normalization_reason?: string | null;
  group_key?: string | null;
  group_reason?: string | null;
  evidence_ids?: number[];
  source_names?: string[];
  approved_for_inventory?: boolean;
  inventory_status?: string;
  inventory_priority?: string | null;
  inventory_note?: string | null;
  approved_at?: string | null;
  approved_reason?: string | null;
  inventory_suggested?: boolean;
}

export interface EntityTrace {
  entity_id: number;
  case_id: number;
  entity_type: string;
  display_value: string;
  normalized_value: string;
  original_values: string[];
  sources: string[];
  evidence_ids: number[];
  evidence_count: number;
  group?: {
    key?: string;
    category?: string;
    priority?: string;
    reason?: string;
    non_destructive?: boolean;
  } | null;
  normalization: {
    reason: string;
    canonical_key?: string | null;
    variant_of?: number | null;
    merge_policy?: string;
    is_normalized_variant?: boolean;
  };
  quality?: { label?: string; reason?: string } | null;
  live_check?: {
    status?: string;
    status_code?: number | null;
    final_url?: string | null;
    checked_at?: string | null;
  } | null;
  review?: {
    review_status: string;
    hidden: boolean;
    hidden_reason?: string | null;
    note?: string | null;
  };
}

export interface DataExplorerCounts {
  total_count: number;
  filtered_count: number;
  visible_count: number;
  hidden_by_filters_count: number;
  hidden_noisy_count: number;
  hidden_historical_count: number;
  hidden_discarded_count: number;
  hidden_false_positive_count: number;
  discarded_count: number;
  historical_count: number;
  noisy_count: number;
  false_positive_count: number;
  evidence_total_count: number;
  evidence_filtered_count: number;
  findings_total_count: number;
  archived_url_findings_count: number;
  url_entity_count: number;
  wayback_entity_limit: number;
  wayback_live_check_batch_limit?: number;
  wayback_scan_url_cap?: number;
  wayback_cdx_fetch_limit?: number;
  max_api_limit: number;
  wayback_original_total?: number;
  wayback_evidence_count?: number;
  wayback_entity_count?: number;
  wayback_grouped_count?: number;
  wayback_visible_count?: number;
  wayback_hidden_by_filters_count?: number;
  wayback_discarded_count?: number;
  wayback_live_200_count?: number;
  wayback_404_count?: number;
  wayback_pending_live_count?: number;
}

export interface CaseDataPayload {
  summary: Record<string, number>;
  counts?: DataExplorerCounts;
  operational_summary?: Record<string, number>;
  wayback_groups?: Record<
    string,
    {
      total: number;
      visible?: number;
      live: number;
      unchecked: number;
      not_found: number;
      discarded?: number;
    }
  >;
  items: CaseDataItem[];
  total: number;
  total_count?: number;
  visible_count?: number;
  filtered_count?: number;
  hidden_by_filters_count?: number;
  total_filtered?: number;
  offset: number;
  limit: number;
  hidden_noisy_count: number;
  hidden_historical_count?: number;
  hidden_discarded_count?: number;
  evidence_total_count?: number;
  evidence_visible_count?: number;
  findings_total_count?: number;
}

export interface QualitySummary {
  case_id: number;
  total_entities: number;
  total_findings: number;
  entities_by_label: Record<string, number>;
  findings_by_label: Record<string, number>;
  top_sources_verified: [string, number][];
  top_sources_noise: [string, number][];
}

export interface JobSummary {
  id: number;
  case_id: number;
  target_type: string;
  target_value: string;
  pivot: boolean;
  status: string;
  findings_count: number;
  scan_record_id: number | null;
  started_at: string;
  finished_at: string | null;
}

export interface GraphPayload {
  nodes: Array<{ data: Record<string, unknown> }>;
  edges: Array<{ data: Record<string, unknown> }>;
}

export interface SourceResultRow {
  id: number;
  case_id: number;
  scan_job_id: number;
  source_name: string;
  status: string;
  findings_count: number;
  started_at: string | null;
  finished_at: string | null;
  latency_ms: number | null;
  message: string | null;
  error_type: string | null;
  created_at: string;
}

export interface EvidenceSummary {
  id: number;
  case_id: number;
  scan_job_id: number;
  source_result_id: number | null;
  entity_id: number | null;
  finding_kind: string | null;
  finding_value: string | null;
  source_name: string;
  evidence_type: string;
  source_url: string | null;
  content_hash_sha256: string;
  hash_short: string;
  collected_at: string;
  sensitive: boolean;
  redacted: boolean;
  live_check?: UrlLiveCheckBrief | null;
}

export interface EvidenceDetail extends EvidenceSummary {
  raw_json: string | null;
  created_at: string;
}
