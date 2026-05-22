import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";
import { bulkCaseReview, getCaseInventory } from "../../api";
import { DataTableShell } from "../../components/DataTableShell";
import { DataTracePanel } from "../../components/DataTracePanel";
import { DataValueCell } from "../../components/DataValueCell";
import { RowActionMenu } from "../../components/RowActionMenu";
import { EmptyState } from "../../components/EmptyState";
import { LiveStatusBadge } from "../../components/LiveStatusBadge";
import { LoadingBlock } from "../../components/LoadingBlock";
import { QualityBadge } from "../../components/QualityBadge";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useI18n } from "../../i18n";
import type { CaseOutletContext } from "./CaseDetail";
import type { CaseDataItem, CaseDataPayload } from "../../types";

function exportInventoryCsv(items: CaseDataItem[]) {
  const header = "type,display_value,inventory_priority,live_status,sources,approved_reason";
  const lines = items.map((it) =>
    [
      it.type,
      `"${it.display_value.replace(/"/g, '""')}"`,
      it.inventory_priority ?? "",
      it.live_status ?? "",
      `"${(it.source_names ?? it.sources).join(";")}"`,
      `"${(it.approved_reason ?? "").replace(/"/g, '""')}"`,
    ].join(","),
  );
  const blob = new Blob([[header, ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "globeye-inventory.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}

export function CaseInventoryPage() {
  const { t } = useI18n();
  const { caseId } = useParams();
  const navigate = useNavigate();
  const id = Number(caseId);
  const { apiKey, bumpRefresh, refreshKey } = useOutletContext<CaseOutletContext>();
  const [payload, setPayload] = useState<CaseDataPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [q, setQ] = useState("");
  const debouncedQ = useDebouncedValue(q);
  const [traceId, setTraceId] = useState<number | null>(null);

  const load = useCallback(() => {
    if (!id) return;
    setLoading(true);
    getCaseInventory(id, apiKey, { q: debouncedQ.trim() || undefined, limit: 500 })
      .then(setPayload)
      .catch(() => setPayload(null))
      .finally(() => setLoading(false));
  }, [apiKey, debouncedQ, id, refreshKey]);

  useEffect(() => {
    load();
  }, [load]);

  const removeFromInventory = async (entityIds: number[]) => {
    if (!id || entityIds.length === 0) return;
    setBusy("inventory");
    try {
      await bulkCaseReview(id, apiKey, {
        entity_ids: entityIds,
        clear_approval: true,
        approved_for_inventory: false,
        inventory_status: "candidate",
      });
      bumpRefresh();
      load();
    } finally {
      setBusy("");
    }
  };

  if (loading && !payload) return <LoadingBlock label={t("inventory_loading")} />;

  const items = payload?.items ?? [];

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600 dark:text-slate-300">{t("inventory_intro")}</p>
      <div className="flex flex-wrap gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("filter_ph")}
          className="rounded border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
        />
        <button
          type="button"
          onClick={() => exportInventoryCsv(items)}
          className="rounded border px-2 py-1 text-xs dark:border-slate-700"
        >
          {t("inventory_export")}
        </button>
      </div>
      {items.length === 0 ? (
        <EmptyState title={t("inventory_empty_title")} description={t("inventory_empty")}>
          <Link to={`/cases/${id}/data`} className="text-sky-600 hover:underline">
            {t("case_raw_data")}
          </Link>
        </EmptyState>
      ) : (
        <DataTableShell
          minWidth={1200}
          footer={
            <p className="border-t border-slate-100 px-3 py-2 text-xs text-slate-500 dark:border-slate-800">
              {items.length} {t("inventory_rows")}
            </p>
          }
        >
          <thead className="sticky top-0 z-10 border-b border-slate-200 bg-white text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900">
            <tr>
              <th className="min-w-[22rem] px-3 py-2">{t("col_value")}</th>
              <th className="px-3 py-2">{t("inventory_priority_col")}</th>
              <th className="px-3 py-2">{t("live_check_col")}</th>
              <th className="min-w-[12rem] px-3 py-2">{t("data_col_actions")}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.id} className="border-b border-slate-100 dark:border-slate-800">
                <td className="px-3 py-2 align-top">
                  <DataValueCell
                    value={row.display_value}
                    badges={<QualityBadge label={row.quality_label} reason={row.quality_reason} />}
                  />
                </td>
                <td className="px-3 py-2">{row.inventory_priority ?? "—"}</td>
                <td className="px-3 py-2">
                  <LiveStatusBadge status={row.live_status} statusCode={row.live_status_code} />
                </td>
                <td className="px-3 py-2 align-top">
                  <RowActionMenu
                    primary={[
                      {
                        key: "remove",
                        label: t("inventory_remove"),
                        onClick: () => removeFromInventory([row.id]),
                        disabled: !!busy,
                        className: "text-red-600",
                      },
                    ]}
                    secondary={[
                      {
                        key: "trace",
                        label: t("trace_btn"),
                        onClick: () => setTraceId(row.id),
                        className: "text-violet-600",
                      },
                      {
                        key: "data",
                        label: t("case_raw_data"),
                        onClick: () => navigate(`/cases/${id}/data`),
                      },
                    ]}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </DataTableShell>
      )}
      {traceId != null ? (
        <DataTracePanel entityId={traceId} apiKey={apiKey} onClose={() => setTraceId(null)} />
      ) : null}
    </div>
  );
}
