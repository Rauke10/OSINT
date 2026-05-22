import type {
  Case,
  CaseCreate,
  CaseDataPayload,
  Entity,
  EntityTrace,
  EvidenceDetail,
  EvidenceSummary,
  GraphPayload,
  HistoryItem,
  JobSummary,
  ScanDepth,
  ScanResult,
  SourceInfo,
  SourceResultRow,
  SourceRoutingPreview,
  SourceStatusRow,
  UrlLiveCheckResult,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function headers(apiKey: string, json = false): HeadersInit {
  const h: Record<string, string> = {};
  if (apiKey) h["X-API-Key"] = apiKey;
  if (json) h["content-type"] = "application/json";
  return h;
}

function formatApiDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        typeof item === "object" && item !== null && "msg" in item
          ? String((item as { msg: unknown }).msg)
          : String(item),
      )
      .join("; ");
  }
  if (detail !== null && detail !== undefined) return String(detail);
  return "";
}

async function parse<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let detail = "";
    try {
      const body = (await r.json()) as { detail?: unknown };
      detail = formatApiDetail(body.detail);
    } catch {
      detail = "";
    }
    throw new ApiError(r.status, detail);
  }
  return (await r.json()) as T;
}

export interface HealthResponse {
  status: string;
  version: string;
  sources: string[];
  api_debug?: boolean;
}

export function getHealth(): Promise<HealthResponse> {
  return fetch("/api/health").then((r) => parse<HealthResponse>(r));
}

export function getSources(): Promise<SourceInfo[]> {
  return fetch("/api/sources").then((r) => parse<SourceInfo[]>(r));
}

export function runScan(
  target: string,
  pivot: boolean,
  apiKey: string,
): Promise<ScanResult> {
  return fetch("/api/scan", {
    method: "POST",
    headers: headers(apiKey, true),
    body: JSON.stringify({ target, pivot }),
  }).then((r) => parse<ScanResult>(r));
}

export function getHistory(apiKey: string): Promise<HistoryItem[]> {
  return fetch("/api/history", { headers: headers(apiKey) }).then((r) =>
    parse<HistoryItem[]>(r),
  );
}

export function getHistoryItem(id: number, apiKey: string): Promise<ScanResult> {
  return fetch(`/api/history/${id}`, { headers: headers(apiKey) }).then((r) =>
    parse<ScanResult>(r),
  );
}

export async function fetchReport(id: number, apiKey: string): Promise<Blob> {
  const r = await fetch(`/api/scan/${id}/report`, { headers: headers(apiKey) });
  if (!r.ok) throw new ApiError(r.status, "report unavailable");
  return r.blob();
}

export function listCases(apiKey: string, includeArchived = false): Promise<Case[]> {
  const q = includeArchived ? "?include_archived=true" : "";
  return fetch(`/api/cases${q}`, { headers: headers(apiKey) }).then((r) =>
    parse<Case[]>(r),
  );
}

export async function deleteCase(caseId: number, apiKey: string): Promise<void> {
  const r = await fetch(`/api/cases/${caseId}`, {
    method: "DELETE",
    headers: headers(apiKey),
  });
  if (!r.ok) {
    let detail = "";
    try {
      const body = (await r.json()) as { detail?: unknown };
      detail = formatApiDetail(body.detail);
    } catch {
      detail = "";
    }
    throw new ApiError(r.status, detail);
  }
}

export function createCase(body: CaseCreate, apiKey: string): Promise<Case> {
  return fetch("/api/cases", {
    method: "POST",
    headers: headers(apiKey, true),
    body: JSON.stringify(body),
  }).then((r) => parse<Case>(r));
}

export function getCase(caseId: number, apiKey: string): Promise<Case> {
  return fetch(`/api/cases/${caseId}`, { headers: headers(apiKey) }).then((r) =>
    parse<Case>(r),
  );
}

export function updateCase(
  caseId: number,
  body: Partial<{ title: string; description: string; status: string }>,
  apiKey: string,
): Promise<Case> {
  return fetch(`/api/cases/${caseId}`, {
    method: "PATCH",
    headers: headers(apiKey, true),
    body: JSON.stringify(body),
  }).then((r) => parse<Case>(r));
}

export function previewSourceRouting(
  target: string,
  depth: ScanDepth,
  apiKey: string,
): Promise<SourceRoutingPreview> {
  return fetch("/api/source-routing/preview", {
    method: "POST",
    headers: headers(apiKey, true),
    body: JSON.stringify({ target, depth }),
  }).then((r) => parse<SourceRoutingPreview>(r));
}

export function runCaseScan(
  caseId: number,
  target: string,
  pivot: boolean,
  apiKey: string,
  depth: ScanDepth = "standard",
): Promise<ScanResult & { job_id: number; case_id: number }> {
  return fetch(`/api/cases/${caseId}/scans`, {
    method: "POST",
    headers: headers(apiKey, true),
    body: JSON.stringify({ target, pivot, depth }),
  }).then((r) => parse<ScanResult & { job_id: number; case_id: number }>(r));
}

export function getCaseData(
  caseId: number,
  apiKey: string,
  params?: {
    type?: string;
    quality?: string;
    source?: string;
    q?: string;
    hide_noisy?: boolean;
    hide_historical?: boolean;
    hide_false_positive?: boolean;
    verified_only?: boolean;
    live_status?: string;
    hide_discarded?: boolean;
    review_status?: string;
    wayback_category?: string;
    wayback_priority?: string;
    operational_status?: string;
    inventory_status?: string;
    only_high_priority?: boolean;
    limit?: number;
    offset?: number;
  },
): Promise<CaseDataPayload> {
  const q = new URLSearchParams();
  if (params?.type) q.set("type", params.type);
  if (params?.quality) q.set("quality", params.quality);
  if (params?.source) q.set("source", params.source);
  if (params?.q) q.set("q", params.q);
  if (params?.hide_noisy != null) q.set("hide_noisy", String(params.hide_noisy));
  if (params?.hide_historical != null) q.set("hide_historical", String(params.hide_historical));
  if (params?.hide_false_positive != null) {
    q.set("hide_false_positive", String(params.hide_false_positive));
  }
  if (params?.verified_only) q.set("verified_only", "true");
  if (params?.live_status) q.set("live_status", params.live_status);
  if (params?.hide_discarded != null) q.set("hide_discarded", String(params.hide_discarded));
  if (params?.review_status) q.set("review_status", params.review_status);
  if (params?.wayback_category) q.set("wayback_category", params.wayback_category);
  if (params?.wayback_priority) q.set("wayback_priority", params.wayback_priority);
  if (params?.operational_status) q.set("operational_status", params.operational_status);
  if (params?.inventory_status) q.set("inventory_status", params.inventory_status);
  if (params?.only_high_priority) q.set("only_high_priority", "true");
  if (params?.limit != null) q.set("limit", String(params.limit));
  if (params?.offset != null) q.set("offset", String(params.offset));
  const qs = q.toString();
  return fetch(`/api/cases/${caseId}/data${qs ? `?${qs}` : ""}`, {
    headers: headers(apiKey),
  }).then((r) => parse<CaseDataPayload>(r));
}

export function getEntityTrace(entityId: number, apiKey: string): Promise<EntityTrace> {
  return fetch(`/api/entities/${entityId}/trace`, { headers: headers(apiKey) }).then((r) =>
    parse(r),
  );
}

export function getCaseInventory(
  caseId: number,
  apiKey: string,
  params?: { q?: string; type?: string; inventory_priority?: string; limit?: number; offset?: number },
): Promise<CaseDataPayload> {
  const q = new URLSearchParams();
  if (params?.q) q.set("q", params.q);
  if (params?.type) q.set("type", params.type);
  if (params?.inventory_priority) q.set("inventory_priority", params.inventory_priority);
  if (params?.limit != null) q.set("limit", String(params.limit));
  if (params?.offset != null) q.set("offset", String(params.offset));
  const qs = q.toString();
  return fetch(`/api/cases/${caseId}/inventory${qs ? `?${qs}` : ""}`, {
    headers: headers(apiKey),
  }).then((r) => parse<CaseDataPayload>(r));
}

export function bulkCaseReview(
  caseId: number,
  apiKey: string,
  body: {
    entity_ids?: number[];
    evidence_ids?: number[];
    values?: string[];
    review_status?: string;
    hidden?: boolean;
    hidden_reason?: string | null;
    note?: string | null;
    approved_for_inventory?: boolean;
    inventory_status?: string;
    inventory_priority?: string | null;
    inventory_note?: string | null;
    approved_reason?: string | null;
    clear_approval?: boolean;
    action?: "approve" | "discard" | "restore" | "remove_inventory";
  },
): Promise<{ updated: number }> {
  return fetch(`/api/cases/${caseId}/data/bulk-review`, {
    method: "POST",
    headers: headers(apiKey, true),
    body: JSON.stringify(body),
  }).then((r) => parse(r));
}

export function getSourcesStatus(apiKey: string, check = false): Promise<SourceStatusRow[]> {
  const q = check ? "?check=true" : "";
  return fetch(`/api/sources/status${q}`, { headers: headers(apiKey) }).then((r) => parse(r));
}

export function postUrlChecks(
  caseId: number,
  apiKey: string,
  body: {
    urls?: string[];
    entries?: { url: string; entity_id?: number | null; evidence_id?: number | null }[];
    method?: string;
    fallback_get?: boolean;
    max_urls?: number;
  },
): Promise<{ checked: number; results: UrlLiveCheckResult[] }> {
  return fetch(`/api/cases/${caseId}/url-checks`, {
    method: "POST",
    headers: headers(apiKey, true),
    body: JSON.stringify(body),
  }).then((r) => parse(r));
}

export function listCaseEntities(caseId: number, apiKey: string): Promise<Entity[]> {
  return fetch(`/api/cases/${caseId}/entities`, { headers: headers(apiKey) }).then(
    (r) => parse<Entity[]>(r),
  );
}

export function getCaseGraph(
  caseId: number,
  apiKey: string,
  mode: "inventory" | "all" | "live" | "high" = "inventory",
): Promise<GraphPayload> {
  return fetch(`/api/cases/${caseId}/graph?mode=${mode}`, { headers: headers(apiKey) }).then(
    (r) => parse<GraphPayload>(r),
  );
}

export function listCaseJobs(caseId: number, apiKey: string): Promise<JobSummary[]> {
  return fetch(`/api/cases/${caseId}/jobs`, { headers: headers(apiKey) }).then((r) =>
    parse<JobSummary[]>(r),
  );
}

export function listCaseSources(
  caseId: number,
  apiKey: string,
  params?: { job_id?: number; status?: string; source_name?: string },
): Promise<SourceResultRow[]> {
  const q = new URLSearchParams();
  if (params?.job_id != null) q.set("job_id", String(params.job_id));
  if (params?.status) q.set("status_filter", params.status);
  if (params?.source_name) q.set("source_name", params.source_name);
  const qs = q.toString();
  return fetch(`/api/cases/${caseId}/sources${qs ? `?${qs}` : ""}`, {
    headers: headers(apiKey),
  }).then((r) => parse<SourceResultRow[]>(r));
}

export function listCaseEvidence(
  caseId: number,
  apiKey: string,
  params?: { job_id?: number; source_name?: string; entity_id?: number },
): Promise<EvidenceSummary[]> {
  const q = new URLSearchParams();
  if (params?.job_id != null) q.set("job_id", String(params.job_id));
  if (params?.source_name) q.set("source_name", params.source_name);
  if (params?.entity_id != null) q.set("entity_id", String(params.entity_id));
  const qs = q.toString();
  return fetch(`/api/cases/${caseId}/evidence${qs ? `?${qs}` : ""}`, {
    headers: headers(apiKey),
  }).then((r) => parse<EvidenceSummary[]>(r));
}

export function getEvidence(evidenceId: number, apiKey: string): Promise<EvidenceDetail> {
  return fetch(`/api/evidence/${evidenceId}`, { headers: headers(apiKey) }).then((r) =>
    parse<EvidenceDetail>(r),
  );
}
