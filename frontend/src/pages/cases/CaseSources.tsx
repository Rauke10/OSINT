import { useEffect, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import { ApiError, getSourcesStatus, listCaseJobs, listCaseSources, previewSourceRouting } from "../../api";
import { EmptyState } from "../../components/EmptyState";
import { LoadingBlock } from "../../components/LoadingBlock";
import { SourceRoutingPreviewPanel } from "../../components/SourceRoutingPreview";
import { useApiAuth } from "../../context/ApiAuthContext";
import { useI18n } from "../../i18n";
import type { CaseOutletContext } from "./CaseDetail";
import type { ScanDepth, SourceResultRow, SourceRoutingPreview, SourceStatusRow } from "../../types";

type LoadState = "loading" | "ok" | "empty" | "error";

const statusBadge: Record<string, string> = {
  used: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  no_results: "bg-sky-500/15 text-sky-700 dark:text-sky-300",
  missing_key: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  invalid_key: "bg-red-500/15 text-red-700 dark:text-red-300",
  rate_limited: "bg-orange-500/15 text-orange-700 dark:text-orange-300",
  network_error: "bg-orange-500/15 text-orange-700 dark:text-orange-300",
  config_error: "bg-red-500/15 text-red-700 dark:text-red-300",
  timeout: "bg-orange-500/15 text-orange-700 dark:text-orange-300",
  failed: "bg-slate-500/15 text-slate-600 dark:text-slate-400",
  not_applicable: "bg-slate-400/15 text-slate-500 dark:text-slate-500",
};

const ACTIVE_STATUSES = new Set([
  "used",
  "no_results",
  "missing_key",
  "invalid_key",
  "rate_limited",
  "network_error",
  "config_error",
  "timeout",
  "failed",
]);

export function CaseSourcesPage() {
  const { t } = useI18n();
  const { caseId } = useParams();
  const id = Number(caseId);
  const { apiKey } = useApiAuth();
  const { caseData } = useOutletContext<CaseOutletContext>();
  const [rows, setRows] = useState<SourceResultRow[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [routingPreview, setRoutingPreview] = useState<SourceRoutingPreview | null>(null);
  const [diagRows, setDiagRows] = useState<SourceStatusRow[]>([]);
  const [diagLoading, setDiagLoading] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoadState("loading");
    listCaseSources(id, apiKey)
      .then((data) => {
        setRows(data);
        setLoadState(data.length === 0 ? "empty" : "ok");
      })
      .catch((e: unknown) => {
        setRows([]);
        setLoadState("error");
        if (e instanceof ApiError) {
          setErrorMessage(e.message ? `Error ${e.status}: ${e.message}` : `Error ${e.status}`);
        } else {
          setErrorMessage(String(e));
        }
      });
  }, [apiKey, id]);

  useEffect(() => {
    if (!id) return;
    listCaseJobs(id, apiKey)
      .then((jobs) => {
        const latest = jobs.find((j) => j.status === "completed");
        if (!latest) return;
        const depth = "standard" as ScanDepth;
        return previewSourceRouting(latest.target_value, depth, apiKey);
      })
      .then((p) => {
        if (p) setRoutingPreview(p);
      })
      .catch(() => undefined);
  }, [apiKey, id]);

  const loadDiag = (check: boolean) => {
    setDiagLoading(true);
    getSourcesStatus(apiKey, check)
      .then(setDiagRows)
      .catch(() => setDiagRows([]))
      .finally(() => setDiagLoading(false));
  };

  useEffect(() => {
    loadDiag(false);
  }, [apiKey]);

  const activeRows = rows.filter((r) => ACTIVE_STATUSES.has(r.status));

  if (loadState === "loading") return <LoadingBlock label={t("sources_loading")} />;

  if (loadState === "error") {
    return (
      <EmptyState title={t("state_backend_error")} description={errorMessage}>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700"
        >
          {t("refresh")}
        </button>
      </EmptyState>
    );
  }

  if (loadState === "empty") {
    return (
      <EmptyState title={t("sources_empty_title")} description={t("sources_empty")}>
        <Link
          to={`/cases/${id}/search`}
          className="rounded-lg bg-sky-600 px-3 py-2 text-sm text-white hover:bg-sky-500"
        >
          {t("case_search")}
        </Link>
      </EmptyState>
    );
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 dark:text-slate-400">{t("sources_trace_intro")}</p>
      {diagRows.length > 0 ? (
        <section className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/50">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-semibold">{t("sources_diag_title")}</h2>
              <p className="mt-1 text-xs text-slate-500">{t("sources_diag_intro")}</p>
            </div>
            <button
              type="button"
              disabled={diagLoading}
              onClick={() => loadDiag(true)}
              className="rounded-lg bg-sky-600 px-3 py-1.5 text-xs text-white hover:bg-sky-500 disabled:opacity-50"
            >
              {diagLoading ? t("sources_probe_running") : t("sources_probe_btn")}
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-400">{t("sources_run_diagnose")}</p>
          <ul className="mt-3 max-h-96 space-y-2 overflow-y-auto text-xs">
            {diagRows.map((d) => (
              <li key={d.name} className="rounded border border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-900">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{d.label ?? d.name}</span>
                  <span
                    className={`rounded px-1 ${
                      d.credential_status === "blocked_by_passive_guard"
                        ? "bg-red-500/15 text-red-700 dark:text-red-300"
                        : "bg-violet-500/10 text-violet-700 dark:text-violet-300"
                    }`}
                  >
                    {t("sources_cred_label")}: {d.credential_status ?? d.status}
                  </span>
                  {d.probe_scan_status ? (
                    <span className="rounded bg-sky-500/10 px-1 text-sky-700 dark:text-sky-300">
                      {t("sources_scan_label")}: {d.probe_scan_status}
                    </span>
                  ) : null}
                  {d.http_status != null ? (
                    <span className="font-mono text-slate-500">HTTP {d.http_status}</span>
                  ) : null}
                  {d.masked_hint ? <span className="font-mono text-slate-400">{d.masked_hint}</span> : null}
                </div>
                {d.checked_endpoint_name ? (
                  <p className="mt-1 text-slate-400">
                    {d.checked_endpoint_name}
                    {d.auth_method ? ` · ${d.auth_method}` : ""}
                  </p>
                ) : null}
                <p className="mt-1 text-slate-500">{d.message}</p>
                {d.provider_error_message_sanitized ? (
                  <p className="text-amber-800 dark:text-amber-200">{d.provider_error_message_sanitized}</p>
                ) : null}
                {d.credential_status === "blocked_by_passive_guard" ? (
                  <p className="text-red-700 dark:text-red-300">{t("sources_guard_blocked_hint")}</p>
                ) : null}
                {d.fix_hint ? <p className="text-amber-700 dark:text-amber-300">{d.fix_hint}</p> : null}
                {d.env_vars?.length ? (
                  <p className="text-slate-400">
                    {t("sources_fix_env")}: {d.env_vars.join(", ")}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {routingPreview ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-sm font-semibold">{t("sources_why_not_title")}</h2>
          <p className="mt-1 text-xs text-slate-500">{t("sources_why_not_intro")}</p>
          {routingPreview.target_type === "email" ? (
            <p className="mt-2 text-xs text-violet-700 dark:text-violet-300">
              {t("sources_email_domain_example")}
            </p>
          ) : null}
          <ul className="mt-3 space-y-3 text-xs">
            {routingPreview.not_applicable.length > 0 ? (
              <li>
                <p className="font-medium text-slate-700 dark:text-slate-300">
                  {t("sources_bucket_not_applicable")}
                </p>
                <ul className="mt-1 list-inside list-disc text-slate-500">
                  {routingPreview.not_applicable.map((e) => (
                    <li key={e.source}>
                      {e.label ?? e.source} — {e.reason}
                    </li>
                  ))}
                </ul>
              </li>
            ) : null}
            {routingPreview.skipped_missing_key.length > 0 ? (
              <li>
                <p className="font-medium text-amber-800 dark:text-amber-200">
                  {t("sources_bucket_missing_key")}
                </p>
                <ul className="mt-1 list-inside list-disc text-amber-700 dark:text-amber-300">
                  {routingPreview.skipped_missing_key.map((e) => (
                    <li key={e.source}>
                      {e.label ?? e.source} — {e.reason}
                    </li>
                  ))}
                </ul>
              </li>
            ) : null}
            {diagRows.filter((d) => d.status === "invalid_key").length > 0 ? (
              <li>
                <p className="font-medium text-red-700 dark:text-red-300">
                  {t("sources_bucket_invalid_key")}
                </p>
                <ul className="mt-1 list-inside list-disc text-red-600 dark:text-red-400">
                  {diagRows
                    .filter((d) => d.status === "invalid_key")
                    .map((d) => (
                      <li key={d.name}>
                        {d.label ?? d.name} — {d.message}
                      </li>
                    ))}
                </ul>
              </li>
            ) : null}
            {routingPreview.skipped_by_depth && routingPreview.skipped_by_depth.length > 0 ? (
              <li>
                <p className="font-medium text-slate-600 dark:text-slate-400">
                  {t("sources_bucket_depth")}
                </p>
                <ul className="mt-1 list-inside list-disc text-slate-500">
                  {routingPreview.skipped_by_depth.map((e) => (
                    <li key={e.source}>
                      {e.label ?? e.source} — {e.reason}
                    </li>
                  ))}
                </ul>
              </li>
            ) : null}
            {routingPreview.disabled && routingPreview.disabled.length > 0 ? (
              <li>
                <p className="font-medium text-slate-600 dark:text-slate-400">
                  {t("sources_bucket_disabled")}
                </p>
                <ul className="mt-1 list-inside list-disc text-slate-500">
                  {routingPreview.disabled.map((e) => (
                    <li key={e.source}>
                      {e.label ?? e.source} — {e.reason}
                    </li>
                  ))}
                </ul>
              </li>
            ) : null}
            {activeRows.filter((r) =>
              ["rate_limited", "network_error", "timeout"].includes(r.status),
            ).length > 0 ? (
              <li>
                <p className="font-medium text-orange-700 dark:text-orange-300">
                  {t("sources_bucket_rate_limit")}
                </p>
                <ul className="mt-1 list-inside list-disc text-orange-600 dark:text-orange-400">
                  {activeRows
                    .filter((r) =>
                      ["rate_limited", "network_error", "timeout"].includes(r.status),
                    )
                    .map((r) => (
                      <li key={r.id}>
                        {r.source_name} — {r.status}
                        {r.message ? `: ${r.message}` : ""}
                      </li>
                    ))}
                </ul>
              </li>
            ) : null}
          </ul>
        </section>
      ) : null}
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800">
            <tr>
              <th className="px-3 py-2">{t("col_tool")}</th>
              <th className="px-3 py-2">{t("col_status")}</th>
              <th className="px-3 py-2">{t("col_findings")}</th>
              <th className="px-3 py-2">{t("sources_latency")}</th>
              <th className="px-3 py-2">{t("sources_job")}</th>
              <th className="px-3 py-2">{t("col_note")}</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {activeRows.map((r) => (
              <tr key={r.id} className="border-b border-slate-100 dark:border-slate-800">
                <td className="px-3 py-2 font-medium">{r.source_name}</td>
                <td className="px-3 py-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      statusBadge[r.status] ?? statusBadge.failed
                    }`}
                  >
                    {r.status}
                  </span>
                </td>
                <td className="px-3 py-2">{r.findings_count}</td>
                <td className="px-3 py-2 text-xs text-slate-500">
                  {r.latency_ms != null ? `${r.latency_ms} ms` : "—"}
                </td>
                <td className="px-3 py-2 font-mono text-xs">#{r.scan_job_id}</td>
                <td className="max-w-xs px-3 py-2 text-xs text-slate-500">{r.message ?? "—"}</td>
                <td className="px-3 py-2">
                  <Link
                    to={`/cases/${id}/evidence?job_id=${r.scan_job_id}&source_name=${encodeURIComponent(r.source_name)}`}
                    className="text-xs text-sky-600 hover:underline dark:text-sky-400"
                  >
                    {t("sources_view_evidence")}
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {routingPreview && routingPreview.not_applicable.length > 0 ? (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            {t("routing_not_applicable_section")}
          </h2>
          <SourceRoutingPreviewPanel
            preview={{
              ...routingPreview,
              will_run: [],
              skipped_missing_key: [],
              warnings: [],
            }}
            loading={false}
            error=""
          />
        </section>
      ) : null}
      {(caseData.jobs_count ?? 0) === 0 ? (
        <p className="text-xs text-slate-400">{t("sources_no_jobs_hint")}</p>
      ) : null}
    </div>
  );
}
