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

export interface Finding {
  source: string;
  target: string;
  timestamp: string;
  confidence: Confidence;
  kind: string;
  value: string;
  normalized_data: Record<string, unknown>;
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

export interface ScanResult {
  scan_id?: number;
  target: TargetRef;
  summary: ScanSummary;
  findings: Finding[];
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
  available: boolean;
  targets: string[];
}
