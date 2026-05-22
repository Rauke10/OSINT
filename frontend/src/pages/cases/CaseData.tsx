import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";
import { ApiError, bulkCaseReview, getCaseData, postUrlChecks } from "../../api";
import { EmptyState } from "../../components/EmptyState";
import { LiveStatusBadge } from "../../components/LiveStatusBadge";
import { LoadingBlock } from "../../components/LoadingBlock";
import { QualityBadge } from "../../components/QualityBadge";
import { DataTracePanel } from "../../components/DataTracePanel";
import { DataTableShell } from "../../components/DataTableShell";
import { DataValueCell } from "../../components/DataValueCell";
import { FilterPanel } from "../../components/FilterPanel";
import { RowActionMenu } from "../../components/RowActionMenu";
import { WaybackGroupingPanel } from "../../components/WaybackGroupingPanel";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useI18n } from "../../i18n";
import type { CaseOutletContext } from "./CaseDetail";
import type { CaseDataItem, CaseDataPayload } from "../../types";

type SectionTab =
  | "all"
  | "domain"
  | "ip"
  | "email"
  | "url"
  | "username"
  | "people"
  | "technical"
  | "noisy";

const TYPE_CARDS: { key: string; labelKey: string }[] = [
  { key: "domain", labelKey: "data_type_domain" },
  { key: "subdomain", labelKey: "data_type_subdomain" },
  { key: "ip", labelKey: "data_type_ip" },
  { key: "email", labelKey: "data_type_email" },
  { key: "url", labelKey: "data_type_url" },
  { key: "username", labelKey: "data_type_username" },
  { key: "phone", labelKey: "data_type_phone" },
  { key: "person", labelKey: "data_type_person" },
  { key: "organization", labelKey: "data_type_org" },
  { key: "finding", labelKey: "data_type_findings" },
  { key: "evidence", labelKey: "data_type_evidence" },
];

const SECTION_TABS: { id: SectionTab; labelKey: string }[] = [
  { id: "all", labelKey: "data_tab_all" },
  { id: "domain", labelKey: "data_tab_domains" },
  { id: "ip", labelKey: "data_tab_ips" },
  { id: "email", labelKey: "data_tab_emails" },
  { id: "url", labelKey: "data_tab_urls" },
  { id: "username", labelKey: "data_tab_usernames" },
  { id: "people", labelKey: "data_tab_people" },
  { id: "technical", labelKey: "data_tab_technical" },
  { id: "noisy", labelKey: "data_tab_noisy" },
];

function sectionTypeFilter(tab: SectionTab): string | undefined {
  if (tab === "all" || tab === "noisy") return undefined;
  if (tab === "people") return "person";
  if (tab === "technical") return "ip";
  return tab;
}

function isWaybackRow(r: CaseDataItem): boolean {
  return Boolean(r.is_wayback_url || (r.type === "url" && r.sources.includes("wayback")));
}

function isCheckableUrl(r: CaseDataItem): boolean {
  return r.type === "url" || /^https?:\/\//i.test(r.display_value);
}

function isCheckableWeb(r: CaseDataItem): boolean {
  return r.type === "url" || r.type === "domain" || r.type === "subdomain" || isCheckableUrl(r);
}

function liveCheckLabelKey(r: CaseDataItem): string {
  if (r.type === "domain" || r.type === "subdomain") return "live_check_btn_web";
  return "live_check_btn_row";
}

type SortKey =
  | "type"
  | "value"
  | "quality"
  | "live"
  | "http"
  | "source"
  | "seen"
  | "checked"
  | "evidence";

function sortRows(rows: CaseDataItem[], key: SortKey, asc: boolean): CaseDataItem[] {
  const dir = asc ? 1 : -1;
  const copy = [...rows];
  copy.sort((a, b) => {
    let cmp = 0;
    switch (key) {
      case "type":
        cmp = a.type.localeCompare(b.type);
        break;
      case "value":
        cmp = a.display_value.localeCompare(b.display_value);
        break;
      case "quality":
        cmp = (a.quality_label ?? "").localeCompare(b.quality_label ?? "");
        break;
      case "live":
        cmp = (a.live_status ?? "").localeCompare(b.live_status ?? "");
        break;
      case "http":
        cmp = (a.live_status_code ?? 0) - (b.live_status_code ?? 0);
        break;
      case "source":
        cmp = (a.sources[0] ?? "").localeCompare(b.sources[0] ?? "");
        break;
      case "seen":
        cmp = a.last_seen_at.localeCompare(b.last_seen_at);
        break;
      case "checked":
        cmp = (a.last_live_checked_at ?? "").localeCompare(b.last_live_checked_at ?? "");
        break;
      case "evidence":
        cmp = a.evidence_count - b.evidence_count;
        break;
    }
    return cmp * dir;
  });
  return copy;
}

const PAGE_SIZES = [25, 50, 100, 250] as const;

const FILTER_TAG_KEYS: Record<string, string> = {
  hide_noisy: "data_filter_tag_hide_noisy",
  hide_historical: "data_filter_tag_hide_historical",
  hide_fp: "data_filter_tag_hide_fp",
  hide_discarded: "data_filter_tag_hide_discarded",
  "quality:verified": "data_filter_tag_quality",
  "quality:likely": "data_filter_tag_quality",
  "quality:historical": "data_filter_tag_quality",
  "quality:unverified": "data_filter_tag_quality",
  "quality:noisy": "data_filter_tag_quality",
  "quality:possible_false_positive": "data_filter_tag_quality",
  "live:not_checked": "data_filter_tag_live",
  "live:live_200": "data_filter_tag_live",
  "live:redirect": "data_filter_tag_live",
  "live:forbidden": "data_filter_tag_live",
  "live:not_found": "data_filter_tag_live",
  "live:server_error": "data_filter_tag_live",
  "live:timeout": "data_filter_tag_live",
  "live:network_error": "data_filter_tag_live",
  "live:invalid_url": "data_filter_tag_live",
  "live:discarded": "data_filter_tag_live",
  source: "data_filter_tag_source",
  search: "data_filter_tag_search",
  wayback_cat: "data_filter_tag_wayback",
  "ops:discarded": "data_filter_tag_ops",
  "ops:active": "data_filter_tag_ops",
  "ops:historical": "data_filter_tag_ops",
};

function exportCsv(items: CaseDataItem[], includeDiscarded: boolean) {
  const rows = includeDiscarded ? items : items.filter((r) => !r.hidden);
  const header = [
    "type",
    "display_value",
    "normalized_value",
    "original_value",
    "canonical_key",
    "variant_of",
    "group_key",
    "group_reason",
    "wayback_category",
    "wayback_priority",
    "quality_label",
    "quality_reason",
    "live_status",
    "live_status_code",
    "sources",
    "evidence_count",
    "evidence_ids",
    "review_status",
    "hidden",
    "hidden_reason",
    "first_seen",
    "last_seen",
  ].join(",");
  const lines = rows.map((it) => {
    const esc = (s: string) => `"${(s ?? "").replace(/"/g, '""')}"`;
    const orig = (it.original_values ?? [it.display_value]).join(" | ");
    return [
      it.type,
      esc(it.display_value),
      esc(it.normalized_value ?? it.value),
      esc(orig),
      esc(it.canonical_key ?? ""),
      it.variant_of != null ? String(it.variant_of) : "",
      esc(it.group_key ?? it.wayback_group_key ?? ""),
      esc(it.group_reason ?? ""),
      it.wayback_category ?? "",
      it.wayback_priority ?? "",
      it.quality_label ?? "",
      esc(it.quality_reason ?? ""),
      it.live_status ?? "",
      it.live_status_code != null ? String(it.live_status_code) : "",
      esc((it.source_names ?? it.sources).join(";")),
      String(it.evidence_count),
      esc((it.evidence_ids ?? []).join(";")),
      it.review_status ?? "",
      it.hidden ? "true" : "false",
      esc(it.hidden_reason ?? ""),
      it.first_seen_at,
      it.last_seen_at,
    ].join(",");
  });
  const blob = new Blob([[header, ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "globeye-case-data.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}

export function CaseDataPage() {
  const { t } = useI18n();
  const { caseId } = useParams();
  const navigate = useNavigate();
  const id = Number(caseId);
  const { caseData, apiKey, refreshKey, bumpRefresh } = useOutletContext<CaseOutletContext>();

  const [payload, setPayload] = useState<CaseDataPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [section, setSection] = useState<SectionTab>("all");
  const [typeCard, setTypeCard] = useState<string | null>(null);
  const [quality, setQuality] = useState<string>("all");
  const [source, setSource] = useState("");
  const [q, setQ] = useState("");
  const debouncedQ = useDebouncedValue(q);
  const [inventoryFilter, setInventoryFilter] = useState("pending");
  const [hideNoisy, setHideNoisy] = useState(false);
  const [hideHistorical, setHideHistorical] = useState(false);
  const [hideFp, setHideFp] = useState(false);
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [liveStatus, setLiveStatus] = useState<string>("all");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [checking, setChecking] = useState(false);
  const [busyAction, setBusyAction] = useState("");
  const [checkMsg, setCheckMsg] = useState("");
  const [hideDiscarded, setHideDiscarded] = useState(false);
  const [pageSize, setPageSize] = useState(50);
  const [pageOffset, setPageOffset] = useState(0);
  const [operational, setOperational] = useState("all");
  const [waybackCategory, setWaybackCategory] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<SortKey>("seen");
  const [sortAsc, setSortAsc] = useState(false);
  const [selectScope, setSelectScope] = useState<"none" | "visible" | "filtered">("none");
  const [traceEntityId, setTraceEntityId] = useState<number | null>(null);

  const queryParams = useCallback(
    (overrides?: { limit?: number; offset?: number }) => {
      const typeFilter =
        typeCard ?? (section === "noisy" ? undefined : sectionTypeFilter(section));
      return {
        type: typeFilter,
        quality: quality === "all" ? undefined : quality,
        source: source || undefined,
        q: debouncedQ.trim() || undefined,
        inventory_status: inventoryFilter,
        hide_noisy: section === "noisy" ? false : hideNoisy,
        hide_historical: hideHistorical,
        hide_false_positive: hideFp,
        verified_only: verifiedOnly,
        live_status: liveStatus === "all" ? undefined : liveStatus,
        wayback_category: waybackCategory ?? undefined,
        operational_status:
          ["all", "important", "with_evidence", "checked", "pending"].includes(operational)
            ? undefined
            : operational === "discarded"
              ? "discarded"
              : operational === "active"
                ? "active"
                : operational === "historical"
                  ? "historical"
                  : undefined,
        hide_discarded:
          inventoryFilter === "discarded"
            ? false
            : operational === "discarded"
              ? false
              : hideDiscarded,
        limit: overrides?.limit ?? pageSize,
        offset: overrides?.offset ?? pageOffset,
      };
    },
    [
      typeCard,
      section,
      quality,
      source,
      debouncedQ,
      inventoryFilter,
      hideNoisy,
      hideHistorical,
      hideFp,
      verifiedOnly,
      liveStatus,
      waybackCategory,
      operational,
      hideDiscarded,
      pageSize,
      pageOffset,
    ],
  );

  const fetchData = useCallback(() => {
    if (!id) return;
    setLoading(true);
    setError("");
    getCaseData(id, apiKey, queryParams())
      .then(setPayload)
      .catch((e: unknown) => {
        setPayload(null);
        if (e instanceof ApiError) {
          setError(e.message ? `Error ${e.status}: ${e.message}` : `Error ${e.status}`);
        } else {
          setError(String(e));
        }
      })
      .finally(() => setLoading(false));
  }, [id, apiKey, queryParams, refreshKey]);

  const showAll = () => {
    setHideNoisy(false);
    setHideHistorical(false);
    setHideFp(false);
    setHideDiscarded(false);
    setQuality("all");
    setLiveStatus("all");
    setOperational("all");
    setWaybackCategory(null);
    setSource("");
    setQ("");
    setInventoryFilter("pending");
    setTypeCard(null);
    setSection("all");
    setPageOffset(0);
  };

  const activeFilters = useMemo(() => {
    const tags: string[] = [];
    if (hideNoisy) tags.push("hide_noisy");
    if (hideHistorical) tags.push("hide_historical");
    if (hideFp) tags.push("hide_fp");
    if (hideDiscarded) tags.push("hide_discarded");
    if (quality !== "all") tags.push(`quality:${quality}`);
    if (liveStatus !== "all") tags.push(`live:${liveStatus}`);
    if (source.trim()) tags.push("source");
    if (q.trim()) tags.push("search");
    if (waybackCategory) tags.push("wayback_cat");
    if (operational !== "all" && !["important", "with_evidence", "checked", "pending"].includes(operational)) {
      tags.push(`ops:${operational}`);
    }
    return tags;
  }, [hideNoisy, hideHistorical, hideFp, hideDiscarded, quality, liveStatus, source, q, waybackCategory, operational]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    setPageOffset(0);
  }, [
    inventoryFilter,
    section,
    typeCard,
    quality,
    source,
    debouncedQ,
    inventoryFilter,
    hideNoisy,
    hideHistorical,
    hideFp,
    hideDiscarded,
    verifiedOnly,
    liveStatus,
    operational,
    waybackCategory,
    pageSize,
  ]);

  const summary = payload?.summary ?? {};
  const rawItems = payload?.items ?? [];
  const counts = payload?.counts;
  const totalCount = counts?.total_count ?? payload?.total_count ?? 0;
  const filteredCount = counts?.filtered_count ?? payload?.filtered_count ?? payload?.total ?? 0;
  const visibleCount = counts?.visible_count ?? payload?.visible_count ?? rawItems.length;
  const hiddenByFilters = counts?.hidden_by_filters_count ?? payload?.hidden_by_filters_count ?? 0;
  const hiddenNoisy = counts?.hidden_noisy_count ?? payload?.hidden_noisy_count ?? 0;
  const discardedTotal = counts?.discarded_count ?? payload?.hidden_discarded_count ?? 0;
  const pageEnd = Math.min(pageOffset + pageSize, filteredCount);
  const totalPages = Math.max(1, Math.ceil(filteredCount / pageSize));
  const currentPage = Math.floor(pageOffset / pageSize) + 1;

  const applyLocalRowFilters = useCallback(
    (rows: CaseDataItem[]) => {
      let list = rows;
      if (section === "people") {
        list = list.filter((r) => r.type === "person" || r.type === "organization");
      }
      if (section === "technical") {
        list = list.filter((r) =>
          ["ip", "subdomain", "domain", "certificate", "service"].includes(r.type),
        );
      }
      if (operational === "important") {
        list = list.filter((r) => ["verified", "likely"].includes(r.quality_label ?? ""));
      }
      if (operational === "with_evidence") {
        list = list.filter((r) => r.evidence_count > 0);
      }
      if (operational === "checked") {
        list = list.filter((r) => r.live_status && r.live_status !== "not_checked");
      }
      if (operational === "pending") {
        list = list.filter(
          (r) => isWaybackRow(r) && (!r.live_status || r.live_status === "not_checked"),
        );
      }
      return sortRows(list, sortBy, sortAsc);
    },
    [section, operational, sortBy, sortAsc],
  );

  const items = useMemo(
    () => applyLocalRowFilters(rawItems),
    [rawItems, applyLocalRowFilters],
  );

  const waybackRows = useMemo(() => items.filter(isWaybackRow), [items]);
  const checkableRows = useMemo(() => items.filter(isCheckableWeb), [items]);
  const ops = payload?.operational_summary ?? {};

  const toggleSelect = (entityId: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(entityId)) next.delete(entityId);
      else next.add(entityId);
      return next;
    });
    setSelectScope("visible");
  };

  const selectVisibleWayback = () => {
    setSelected(new Set(waybackRows.map((r) => r.id)));
    setSelectScope("visible");
  };

  const deselectAll = () => {
    setSelected(new Set());
    setSelectScope("none");
  };

  const selectAllFiltered = async () => {
    if (!id) return;
    const data = await getCaseData(id, apiKey, {
      ...queryParams({ limit: 2000, offset: 0 }),
    });
    const ids = data.items.filter(isWaybackRow).map((r) => r.id);
    setSelected(new Set(ids));
    setSelectScope("filtered");
  };

  const exportAllFiltered = async () => {
    if (!id) return;
    const data = await getCaseData(id, apiKey, queryParams({ limit: 2000, offset: 0 }));
    exportCsv(applyLocalRowFilters(data.items), !hideDiscarded);
  };

  const afterMutation = () => {
    setSelected(new Set());
    bumpRefresh();
    fetchData();
  };

  const bulkDiscard = async (entityIds: number[], reason: string) => {
    if (!id || entityIds.length === 0) return;
    setBusyAction("discarding");
    try {
      await bulkCaseReview(id, apiKey, {
        entity_ids: entityIds,
        action: "discard",
        hidden_reason: reason,
      });
      afterMutation();
    } finally {
      setBusyAction("");
    }
  };

  const bulkRestore = async (entityIds: number[]) => {
    if (!id || entityIds.length === 0) return;
    setBusyAction("restoring");
    try {
      await bulkCaseReview(id, apiKey, {
        entity_ids: entityIds,
        action: "restore",
      });
      afterMutation();
    } finally {
      setBusyAction("");
    }
  };

  const bulkApproveInventory = async (entityIds: number[]) => {
    if (!id || entityIds.length === 0) return;
    setBusyAction("approving");
    try {
      await bulkCaseReview(id, apiKey, {
        entity_ids: entityIds,
        action: "approve",
      });
      afterMutation();
    } finally {
      setBusyAction("");
    }
  };

  const removeFromInventory = async (entityIds: number[]) => {
    if (!id || entityIds.length === 0) return;
    setBusyAction("inventory");
    try {
      await bulkCaseReview(id, apiKey, {
        entity_ids: entityIds,
        action: "remove_inventory",
      });
      afterMutation();
    } finally {
      setBusyAction("");
    }
  };

  const runLiveChecks = async (rows: CaseDataItem[]) => {
    if (!id || rows.length === 0) return;
    const batch = rows.slice(0, 25);
    setChecking(true);
    setCheckMsg("");
    try {
      await postUrlChecks(id, apiKey, {
        entries: batch.map((r) => ({
          url:
            r.type === "domain" || r.type === "subdomain"
              ? r.display_value
              : r.display_value.startsWith("http")
                ? r.display_value
                : r.value,
          entity_id: r.id,
        })),
        method: "HEAD",
        fallback_get: true,
        max_urls: 25,
      });
      setCheckMsg(t("live_check_done"));
      afterMutation();
    } catch (e: unknown) {
      setCheckMsg(e instanceof ApiError ? e.message : String(e));
    } finally {
      setChecking(false);
    }
  };

  const activeTypeForCard = useMemo(() => {
    if (typeCard) return typeCard;
    if (section !== "all" && section !== "noisy" && section !== "people" && section !== "technical") {
      return section;
    }
    return null;
  }, [typeCard, section]);

  if (loading && !payload) {
    return <LoadingBlock label={t("data_loading")} />;
  }

  if (error) {
    return (
      <EmptyState title={t("state_backend_error")} description={error}>
        <button
          type="button"
          onClick={fetchData}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700"
        >
          {t("refresh")}
        </button>
      </EmptyState>
    );
  }

  if (!payload || payload.summary.total_items === 0) {
    return (
      <EmptyState title={t("data_empty_title")} description={t("data_empty")}>
        <Link
          to={`/cases/${id}/search`}
          className="rounded-lg bg-sky-600 px-3 py-2 text-sm text-white hover:bg-sky-500"
        >
          {t("case_search")}
        </Link>
      </EmptyState>
    );
  }

  const noFilterResults = items.length === 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">{t("case_raw_data")}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">{t("data_subtitle")}</p>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{t("data_explainer_main")}</p>
        <ul className="mt-2 list-inside list-disc text-xs text-slate-500 dark:text-slate-400">
          <li>{t("data_help_datos")}</li>
          <li>{t("data_help_evidencias")}</li>
          <li>{t("data_help_hallazgos")}</li>
          <li>{t("data_help_verified")}</li>
          <li>{t("data_help_historical")}</li>
        </ul>
        <p className="mt-3 rounded-lg bg-slate-100 px-3 py-2 text-sm dark:bg-slate-800">
          {t("data_stats_line")
            .replace("{visible}", String(visibleCount))
            .replace("{filtered}", String(filteredCount))
            .replace("{total}", String(totalCount))
            .replace("{evidence}", String(counts?.evidence_total_count ?? summary.evidence ?? 0))
            .replace("{findings}", String(counts?.findings_total_count ?? summary.finding ?? 0))
            .replace("{hidden}", String(hiddenByFilters))}
        </p>
        {counts && (counts.wayback_original_total ?? counts.archived_url_findings_count) > 0 ? (
          <div className="mt-3 space-y-2 rounded-lg border border-violet-200 bg-violet-50/60 p-3 text-xs dark:border-violet-900 dark:bg-violet-950/30">
            <p className="text-violet-900 dark:text-violet-200">{t("data_wayback_audit_intro")}</p>
            <ul className="grid gap-1 sm:grid-cols-2">
              <li>
                {t("data_wb_orig")}: {counts.wayback_original_total ?? counts.archived_url_findings_count}
              </li>
              <li>
                {t("data_wb_evidence")}: {counts.wayback_evidence_count ?? counts.evidence_total_count}
              </li>
              <li>
                {t("data_wb_entities")}: {counts.wayback_entity_count ?? counts.url_entity_count}
              </li>
              <li>
                {t("data_wb_visible")}: {counts.wayback_visible_count ?? visibleCount}
              </li>
              <li>
                {t("data_wb_hidden")}: {counts.wayback_hidden_by_filters_count ?? hiddenByFilters}
              </li>
              <li>
                {t("data_wb_discarded")}: {counts.wayback_discarded_count ?? 0}
              </li>
              <li>
                {t("data_wb_200")}: {counts.wayback_live_200_count ?? 0}
              </li>
              <li>
                {t("data_wb_404")}: {counts.wayback_404_count ?? 0}
              </li>
              <li>
                {t("data_wb_pending")}: {counts.wayback_pending_live_count ?? 0}
              </li>
            </ul>
            <p className="text-violet-700 dark:text-violet-300">
              {t("data_wayback_cap_note")
                .replace("{findings}", String(counts.wayback_original_total ?? counts.archived_url_findings_count))
                .replace("{entities}", String(counts.wayback_entity_count ?? counts.url_entity_count))
                .replace(
                  "{limit}",
                  String(counts.wayback_scan_url_cap ?? counts.wayback_cdx_fetch_limit ?? 200),
                )}
            </p>
            <p className="text-slate-600 dark:text-slate-400">{t("data_live_batch_note")}</p>
            <Link
              to={`/cases/${id}/evidence?source_name=wayback`}
              className="inline-block text-sky-600 hover:underline dark:text-sky-400"
            >
              {t("data_wayback_evidence_link")}
            </Link>
          </div>
        ) : null}
        {(activeFilters.length > 0 || hiddenByFilters > 0) && (
          <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-800 dark:bg-amber-950/40">
            <p className="font-medium text-amber-900 dark:text-amber-200">{t("data_hidden_banner")}</p>
            {activeFilters.length > 0 ? (
              <ul className="mt-1 list-inside list-disc text-xs">
                {activeFilters.map((f) => (
                  <li key={f}>{t((FILTER_TAG_KEYS[f] ?? "data_filter_tag_generic") as "data_filter_tag_generic")}</li>
                ))}
              </ul>
            ) : null}
            <button
              type="button"
              onClick={showAll}
              className="mt-2 rounded bg-amber-700 px-2 py-1 text-xs text-white hover:bg-amber-600"
            >
              {t("data_show_all")}
            </button>
          </div>
        )}
        {waybackRows.length > 0 ? (
          <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
            <p>{t("live_check_warning")}</p>
            <p className="mt-1 text-xs">{t("live_check_batch_limit")}</p>
          </div>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-slate-100 px-2 py-1 dark:bg-slate-800">
          {t("ops_total")}: {ops.total_assets ?? summary.total_items ?? 0}
        </span>
        <span className="rounded-full bg-emerald-100 px-2 py-1 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
          {t("ops_active")}: {ops.active ?? 0}
        </span>
        <span className="rounded-full bg-amber-100 px-2 py-1 dark:bg-amber-900/40">
          {t("ops_pending")}: {ops.pending_live_check ?? 0}
        </span>
        <span className="rounded-full bg-slate-200 px-2 py-1">
          {t("ops_discarded")}: {ops.discarded ?? payload?.hidden_discarded_count ?? 0}
        </span>
      </div>

      {Object.keys(payload.wayback_groups ?? {}).length > 0 ? (
        <WaybackGroupingPanel
          groups={payload.wayback_groups ?? {}}
          activeCategory={waybackCategory}
          onSelectCategory={(c) => {
            setWaybackCategory(c);
            setSection("url");
            setTypeCard(null);
            setPageOffset(0);
          }}
          onViewUrls={(c) => {
            setWaybackCategory(c);
            setSection("url");
            setTypeCard("url");
            setPageOffset(0);
          }}
          onCheckHighPriority={() => {
            const high = items.filter(
              (r) => r.wayback_priority === "high" && r.live_status === "not_checked",
            );
            if (high.length > 25) setCheckMsg(t("batch_limit_hint"));
            runLiveChecks(high);
          }}
          checking={checking}
        />
      ) : null}

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {TYPE_CARDS.map((card) => {
          const total =
            card.key === "evidence"
              ? (counts?.evidence_total_count ?? summary.evidence ?? 0)
              : card.key === "finding"
                ? (counts?.findings_total_count ?? summary.finding ?? 0)
                : (summary[card.key] ?? 0);
          const visibleForType =
            activeTypeForCard === card.key ? filteredCount : total;
          if (card.key === "finding") {
            return (
              <div
                key={card.key}
                className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900/50"
              >
                <p className="text-xs text-slate-500">{t(card.labelKey)}</p>
                <p className="text-2xl font-semibold">{total}</p>
                <p className="text-xs text-slate-400">{t("data_card_total")}</p>
                <p className="mt-1 text-xs text-slate-500">{t("data_help_hallazgos_short")}</p>
              </div>
            );
          }
          if (card.key === "evidence") {
            return (
              <Link
                key={card.key}
                to={`/cases/${id}/evidence`}
                className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900/50 hover:border-sky-400"
              >
                <p className="text-xs text-slate-500">{t(card.labelKey)}</p>
                <p className="text-2xl font-semibold">{total}</p>
                <p className="text-xs text-slate-400">{t("data_card_total")}</p>
              </Link>
            );
          }
          const active = activeTypeForCard === card.key;
          return (
            <button
              key={card.key}
              type="button"
              onClick={() => {
                setTypeCard(active ? null : card.key);
                setSection("all");
                setPageOffset(0);
              }}
              className={`rounded-xl border p-3 text-left transition ${
                active
                  ? "border-sky-500 bg-sky-500/10"
                  : "border-slate-200 bg-white hover:border-sky-400 dark:border-slate-800 dark:bg-slate-900"
              }`}
            >
              <p className="text-xs text-slate-500">{t(card.labelKey)}</p>
              <p className="text-2xl font-semibold">{total}</p>
              <p className="text-xs text-slate-400">
                {active
                  ? t("data_card_visible_filtered").replace("{n}", String(visibleForType))
                  : t("data_card_total")}
              </p>
              {card.key === "url" &&
              counts &&
              (counts.wayback_original_total ?? counts.archived_url_findings_count) >
                (counts.wayback_scan_url_cap ?? 200) ? (
                <p className="text-xs text-violet-600 dark:text-violet-400">
                  {t("data_card_wayback_truncated").replace(
                    "{n}",
                    String(counts.wayback_original_total ?? counts.archived_url_findings_count),
                  )}
                </p>
              ) : null}
            </button>
          );
        })}
        {(summary.possible_false_positive ?? 0) > 0 ? (
          <button
            type="button"
            onClick={() => {
              setQuality("possible_false_positive");
              setHideFp(false);
            }}
            className="rounded-xl border border-red-200 bg-red-500/5 p-3 text-left dark:border-red-900"
          >
            <p className="text-xs text-red-600 dark:text-red-400">{t("data_fp_card")}</p>
            <p className="text-2xl font-semibold">{summary.possible_false_positive}</p>
          </button>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        {SECTION_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => {
              setSection(tab.id);
              setTypeCard(null);
              if (tab.id === "noisy") setHideNoisy(false);
            }}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              section === tab.id
                ? "bg-sky-600 text-white"
                : "border border-slate-300 dark:border-slate-700"
            }`}
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      <FilterPanel title={t("filter_panel_primary")}>
        <label className="text-sm">
          <span className="text-xs text-slate-500">{t("inventory_filter_label")}</span>
          <select
            value={inventoryFilter}
            onChange={(e) => setInventoryFilter(e.target.value)}
            className="mt-1 block min-w-[10rem] rounded border border-slate-300 bg-slate-50 px-2 py-1 dark:border-slate-700 dark:bg-slate-800"
          >
            <option value="pending">{t("inventory_filter_pending")}</option>
            <option value="not_approved">{t("inventory_filter_not_approved")}</option>
            <option value="approved">{t("inventory_filter_in_inventory")}</option>
            <option value="discarded">{t("inventory_filter_discarded")}</option>
            <option value="all">{t("inventory_filter_all")}</option>
          </select>
        </label>
        <label className="text-sm">
          <span className="text-xs text-slate-500">{t("col_source")}</span>
          <input
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="rdap, crtsh…"
            className="mt-1 block w-40 rounded border border-slate-300 bg-slate-50 px-2 py-1 dark:border-slate-700 dark:bg-slate-800"
          />
        </label>
        <label className="min-w-[12rem] flex-1 text-sm lg:min-w-[16rem]">
          <span className="text-xs text-slate-500">{t("filter_ph")}</span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="mt-1 w-full min-w-[12rem] rounded border border-slate-300 bg-slate-50 px-2 py-1 dark:border-slate-700 dark:bg-slate-800"
          />
        </label>
      </FilterPanel>

      <FilterPanel title={t("filter_panel_status")}>
        <label className="text-sm">
          <span className="text-xs text-slate-500">{t("quality_col")}</span>
          <select
            value={quality}
            onChange={(e) => setQuality(e.target.value)}
            className="mt-1 block rounded border border-slate-300 bg-slate-50 px-2 py-1 dark:border-slate-700 dark:bg-slate-800"
          >
            <option value="all">{t("data_filter_all")}</option>
            <option value="verified">{t("quality_verified")}</option>
            <option value="likely">{t("quality_likely")}</option>
            <option value="historical">{t("quality_historical")}</option>
            <option value="unverified">{t("quality_unverified")}</option>
            <option value="noisy">{t("quality_noisy")}</option>
            <option value="possible_false_positive">{t("quality_possible_false_positive")}</option>
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-xs">
          <input type="checkbox" checked={hideNoisy} onChange={(e) => setHideNoisy(e.target.checked)} />
          {t("data_hide_noisy_only")}
        </label>
        <label className="flex items-center gap-1.5 text-xs">
          <input
            type="checkbox"
            checked={hideHistorical}
            onChange={(e) => setHideHistorical(e.target.checked)}
          />
          {t("data_hide_historical")}
        </label>
        <label className="flex items-center gap-1.5 text-xs">
          <input type="checkbox" checked={hideFp} onChange={(e) => setHideFp(e.target.checked)} />
          {t("quality_filter_hide_fp")}
        </label>
        <label className="flex items-center gap-1.5 text-xs">
          <input
            type="checkbox"
            checked={verifiedOnly}
            onChange={(e) => setVerifiedOnly(e.target.checked)}
          />
          {t("quality_filter_verified")}
        </label>
        <label className="text-sm">
          <span className="text-xs text-slate-500">{t("ops_filter_label")}</span>
          <select
            value={operational}
            onChange={(e) => setOperational(e.target.value)}
            className="mt-1 block rounded border border-slate-300 bg-slate-50 px-2 py-1 dark:border-slate-700 dark:bg-slate-800"
          >
            <option value="all">{t("ops_all")}</option>
            <option value="active">{t("ops_active_only")}</option>
            <option value="checked">{t("ops_checked")}</option>
            <option value="pending">{t("ops_pending_only")}</option>
            <option value="discarded">{t("ops_discarded_only")}</option>
            <option value="important">{t("ops_important")}</option>
            <option value="with_evidence">{t("ops_with_evidence")}</option>
            <option value="historical">{t("ops_historical")}</option>
          </select>
        </label>
        <label className="text-sm">
          <span className="text-xs text-slate-500">{t("live_filter_label")}</span>
          <select
            value={liveStatus}
            onChange={(e) => setLiveStatus(e.target.value)}
            className="mt-1 block rounded border border-slate-300 bg-slate-50 px-2 py-1 dark:border-slate-700 dark:bg-slate-800"
          >
            <option value="all">{t("live_filter_all")}</option>
            <option value="not_checked">{t("live_filter_not_checked")}</option>
            <option value="live_200">{t("live_status_live_200")}</option>
            <option value="redirect">{t("live_status_redirect")}</option>
            <option value="forbidden">{t("live_status_forbidden")}</option>
            <option value="not_found">{t("live_status_not_found")}</option>
            <option value="server_error">{t("live_status_server_error")}</option>
            <option value="timeout">{t("live_status_timeout")}</option>
            <option value="network_error">{t("live_status_network_error")}</option>
            <option value="invalid_url">{t("live_status_invalid_url")}</option>
            <option value="discarded">{t("live_filter_discarded")}</option>
          </select>
        </label>
        <label className="text-sm">
          <span className="text-xs text-slate-500">{t("sort_label")}</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortKey)}
            className="mt-1 block rounded border border-slate-300 bg-slate-50 px-2 py-1 dark:border-slate-700 dark:bg-slate-800"
          >
            <option value="type">{t("sort_type")}</option>
            <option value="value">{t("sort_value")}</option>
            <option value="quality">{t("sort_quality")}</option>
            <option value="live">{t("sort_live")}</option>
            <option value="http">{t("sort_http")}</option>
            <option value="source">{t("sort_source")}</option>
            <option value="seen">{t("sort_seen")}</option>
            <option value="checked">{t("sort_checked")}</option>
            <option value="evidence">{t("sort_evidence")}</option>
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-xs pt-5">
          <input type="checkbox" checked={sortAsc} onChange={(e) => setSortAsc(e.target.checked)} />
          ASC
        </label>
        <label className="flex items-center gap-1.5 text-xs">
          <input
            type="checkbox"
            checked={hideDiscarded}
            onChange={(e) => setHideDiscarded(e.target.checked)}
          />
          {t("hide_discarded_label")}
        </label>
        <button
          type="button"
          onClick={() => {
            setHideDiscarded(false);
            setOperational("discarded");
          }}
          className="rounded-lg border px-2 py-1 text-xs dark:border-slate-700"
        >
          {t("show_discarded_btn")} ({discardedTotal})
        </button>
      </FilterPanel>

      <FilterPanel title={t("filter_panel_bulk")}>
        <label className="text-sm">
          <span className="text-xs text-slate-500">{t("data_page_size")}</span>
          <select
            value={pageSize}
            onChange={(e) => setPageSize(Number(e.target.value))}
            className="mt-1 block rounded border border-slate-300 bg-slate-50 px-2 py-1 dark:border-slate-700 dark:bg-slate-800"
          >
            {PAGE_SIZES.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        {checkableRows.length > 0 ? (
          <>
            <p className="w-full text-xs text-amber-700 dark:text-amber-400">
              {t("live_check_active_warning")}
            </p>
            <button
              type="button"
              onClick={() => {
                setSelected(new Set(checkableRows.map((r) => r.id)));
                setSelectScope("visible");
              }}
              className="rounded-lg border px-2 py-1 text-xs dark:border-slate-700"
            >
              {t("select_visible_urls")}
            </button>
            <button type="button" onClick={deselectAll} className="rounded-lg border px-2 py-1 text-xs dark:border-slate-700">
              {t("deselect_visible")}
            </button>
            <button type="button" onClick={() => void selectAllFiltered()} className="rounded-lg border px-2 py-1 text-xs dark:border-slate-700">
              {t("select_all_filtered")}
            </button>
            <button
              type="button"
              disabled={checking || selected.size === 0}
              onClick={() => {
                const urls = items.filter((r) => selected.has(r.id) && isCheckableWeb(r));
                if (urls.length > 25) setCheckMsg(t("batch_limit_hint"));
                runLiveChecks(urls.slice(0, 25));
              }}
              className="rounded-lg bg-amber-600 px-3 py-1.5 text-sm text-white hover:bg-amber-500 disabled:opacity-50"
            >
              {checking ? t("live_check_running") : t("live_check_btn_batch")}
              {selected.size > 0 ? ` (${selected.size})` : ""}
            </button>
          </>
        ) : null}
        <button
          type="button"
          disabled={selected.size === 0}
          onClick={() => bulkDiscard([...selected], "manual discard")}
          className="rounded-lg border border-red-300 px-2 py-1 text-xs text-red-700 dark:border-red-800"
        >
          {t("discard_selected")}
        </button>
        <button
          type="button"
          onClick={() =>
            bulkDiscard(
              items.filter((r) => r.live_status === "not_found").map((r) => r.id),
              "404 not found",
            )
          }
          className="rounded-lg border border-red-300 px-2 py-1 text-xs text-red-700 dark:border-red-800"
        >
          {t("discard_404_filtered")}
        </button>
        <button
          type="button"
          disabled={selected.size === 0}
          onClick={() => bulkRestore([...selected])}
          className="rounded-lg border px-2 py-1 text-xs dark:border-slate-700"
        >
          {busyAction === "restoring" ? t("restoring") : t("restore_selected")}
        </button>
        <button
          type="button"
          disabled={selected.size === 0 || !!busyAction}
          onClick={() => bulkApproveInventory([...selected])}
          className="rounded-lg border border-emerald-400 px-2 py-1 text-xs text-emerald-800 dark:border-emerald-800"
        >
          {busyAction === "approving" ? t("approving") : t("inventory_approve_selected")}
        </button>
        <Link
          to={`/cases/${id}/inventory`}
          className="rounded-lg border px-2 py-1 text-xs dark:border-slate-700"
        >
          {t("case_inventory")} →
        </Link>
        {selectScope !== "none" ? (
          <p className="w-full text-xs text-slate-500">
            {selectScope === "filtered" ? t("select_scope_filtered") : t("select_scope_visible")}
          </p>
        ) : null}
        {checkMsg ? <p className="text-xs text-slate-500">{checkMsg}</p> : null}
        <button
          type="button"
          onClick={() => exportCsv(items, !hideDiscarded)}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700"
        >
          {t("data_export_csv")}
        </button>
        <button
          type="button"
          onClick={() => void exportAllFiltered()}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700"
        >
          {t("data_export_csv_all")}
        </button>
      </FilterPanel>

      {hiddenNoisy > 0 && hideNoisy ? (
        <p className="text-sm text-violet-700 dark:text-violet-300">
          {t("data_hidden_noisy").replace("{n}", String(hiddenNoisy))}
        </p>
      ) : null}

      {noFilterResults ? (
        <EmptyState title={t("data_no_filter")} description={t("data_hidden_only")} />
      ) : (
        <DataTableShell
          minWidth={1400}
          footer={
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 px-3 py-2 text-xs text-slate-500 dark:border-slate-800">
              <p>
                {t("data_pagination_line")
                  .replace("{from}", String(filteredCount === 0 ? 0 : pageOffset + 1))
                  .replace("{to}", String(pageEnd))
                  .replace("{filtered}", String(filteredCount))
                  .replace("{total}", String(totalCount))}
              </p>
              <p className="text-slate-400">
                {t("data_api_limit_note").replace("{max}", String(counts?.max_api_limit ?? 2000))}
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={pageOffset <= 0}
                  onClick={() => setPageOffset((o) => Math.max(0, o - pageSize))}
                  className="rounded border px-2 py-0.5 disabled:opacity-40 dark:border-slate-700"
                >
                  {t("data_page_prev")}
                </button>
                <span>
                  {t("data_page_num")
                    .replace("{page}", String(currentPage))
                    .replace("{pages}", String(totalPages))}
                </span>
                <button
                  type="button"
                  disabled={pageEnd >= filteredCount}
                  onClick={() => setPageOffset((o) => o + pageSize)}
                  className="rounded border px-2 py-0.5 disabled:opacity-40 dark:border-slate-700"
                >
                  {t("data_page_next")}
                </button>
              </div>
            </div>
          }
        >
          <thead className="sticky top-0 z-10 border-b border-slate-200 bg-white text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900">
              <tr>
                {waybackRows.length > 0 ? (
                  <th className="w-8 px-2 py-2">
                    <input
                      type="checkbox"
                      checked={waybackRows.length > 0 && waybackRows.every((r) => selected.has(r.id))}
                      onChange={(e) => (e.target.checked ? selectVisibleWayback() : deselectAll())}
                      aria-label={t("select_visible")}
                    />
                  </th>
                ) : null}
                <th className="px-3 py-2">{t("data_col_type")}</th>
                <th className="min-w-[22rem] px-3 py-2">{t("col_value")}</th>
                <th className="px-3 py-2">{t("quality_col")}</th>
                {waybackRows.length > 0 ? (
                  <th className="px-3 py-2">{t("live_check_col")}</th>
                ) : null}
                <th className="px-3 py-2">{t("data_col_sources")}</th>
                <th className="px-3 py-2">{t("entity_last_seen")}</th>
                <th className="px-3 py-2">{t("data_col_jobs")}</th>
                <th className="px-3 py-2">{t("data_type_evidence")}</th>
                <th className="min-w-[14rem] px-3 py-2">{t("data_col_actions")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => {
                const isWayback = isWaybackRow(row);
                return (
                <tr key={row.id} className="border-b border-slate-100 dark:border-slate-800">
                  {waybackRows.length > 0 ? (
                    <td className="px-2 py-2">
                      {isWayback ? (
                        <input
                          type="checkbox"
                          checked={selected.has(row.id)}
                          onChange={() => toggleSelect(row.id)}
                          aria-label={row.display_value}
                        />
                      ) : null}
                    </td>
                  ) : null}
                  <td className="px-3 py-2 font-mono text-xs">{row.type}</td>
                  <td className="px-3 py-2 align-top">
                    <DataValueCell
                      value={row.display_value}
                      badges={
                        <>
                          {row.hidden ? (
                            <span className="text-xs text-red-500">({t("ops_discarded")})</span>
                          ) : null}
                          {row.approved_for_inventory ? (
                            <span className="text-xs text-emerald-600">
                              ({t("inventory_approved_badge")})
                            </span>
                          ) : row.inventory_suggested ? (
                            <span className="text-xs text-amber-600">
                              ({t("inventory_suggested_badge")})
                            </span>
                          ) : null}
                        </>
                      }
                    />
                  </td>
                  <td className="px-3 py-2">
                    <QualityBadge label={row.quality_label} reason={row.quality_reason} />
                  </td>
                  {waybackRows.length > 0 ? (
                    <td className="px-3 py-2">
                      {isWayback ? (
                        <LiveStatusBadge
                          status={row.live_status}
                          statusCode={row.live_status_code}
                        />
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  ) : null}
                  <td className="px-3 py-2 text-xs text-slate-500">{row.sources.join(", ") || "—"}</td>
                  <td className="px-3 py-2 text-xs text-slate-500">
                    {new Date(row.last_seen_at).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {row.first_job_id != null ? `#${row.first_job_id}` : "—"}
                    {row.last_job_id != null && row.last_job_id !== row.first_job_id
                      ? ` → #${row.last_job_id}`
                      : ""}
                  </td>
                  <td className="px-3 py-2">{row.evidence_count}</td>
                  <td className="px-3 py-2 align-top">
                    <RowActionMenu
                      primary={[
                        ...(row.evidence_count > 0
                          ? [
                              {
                                key: "evidence",
                                label: t("sources_view_evidence"),
                                onClick: () =>
                                  navigate(`/cases/${id}/evidence?entity_id=${row.id}`),
                              },
                            ]
                          : []),
                        ...(isCheckableWeb(row)
                          ? [
                              {
                                key: "check",
                                label: t(liveCheckLabelKey(row)),
                                onClick: () => runLiveChecks([row]),
                                disabled: checking,
                                className: "text-amber-700 dark:text-amber-400",
                              },
                            ]
                          : []),
                        row.approved_for_inventory
                          ? {
                              key: "inv-remove",
                              label: t("inventory_remove"),
                              onClick: () => removeFromInventory([row.id]),
                              disabled: !!busyAction,
                              className: "text-red-600",
                            }
                          : {
                              key: "inv-approve",
                              label: t("inventory_approve_row"),
                              onClick: () => bulkApproveInventory([row.id]),
                              disabled: !!busyAction || row.hidden,
                              className: "text-emerald-700 dark:text-emerald-400",
                            },
                      ]}
                      secondary={[
                        {
                          key: "trace",
                          label: t("trace_btn"),
                          onClick: () => setTraceEntityId(row.id),
                        },
                        {
                          key: "graph",
                          label: t("data_view_graph"),
                          onClick: () => navigate(`/cases/${id}/graph`),
                        },
                        ...(row.hidden
                          ? [
                              {
                                key: "restore",
                                label: t("restore_selected"),
                                onClick: () => bulkRestore([row.id]),
                              },
                            ]
                          : [
                              {
                                key: "discard",
                                label: t("discard_selected"),
                                onClick: () => bulkDiscard([row.id], "manual"),
                                className: "text-red-600",
                              },
                            ]),
                      ]}
                    />
                  </td>
                </tr>
              );
              })}
            </tbody>
        </DataTableShell>
      )}

      {(caseData.jobs_count ?? 0) > 0 ? (
        <p className="text-xs text-slate-400">
          {t("data_sources_hint")}{" "}
          <Link to={`/cases/${id}/sources`} className="text-sky-600 hover:underline dark:text-sky-400">
            {t("case_sources")}
          </Link>
        </p>
      ) : null}
      {traceEntityId != null ? (
        <DataTracePanel
          entityId={traceEntityId}
          apiKey={apiKey}
          onClose={() => setTraceEntityId(null)}
        />
      ) : null}
    </div>
  );
}
