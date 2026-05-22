import { useEffect, useState } from "react";
import { Link, useOutletContext, useParams, useSearchParams } from "react-router-dom";
import { ApiError, bulkCaseReview, getEvidence, listCaseEvidence, postUrlChecks } from "../../api";
import { DataTableShell } from "../../components/DataTableShell";
import { DataValueCell } from "../../components/DataValueCell";
import { EmptyState } from "../../components/EmptyState";
import { LiveStatusBadge } from "../../components/LiveStatusBadge";
import { LoadingBlock } from "../../components/LoadingBlock";
import { RowActionMenu } from "../../components/RowActionMenu";
import { useApiAuth } from "../../context/ApiAuthContext";
import { useI18n } from "../../i18n";
import type { CaseOutletContext } from "./CaseDetail";
import type { EvidenceDetail, EvidenceSummary } from "../../types";

type LoadState = "loading" | "ok" | "empty" | "error";

export function CaseEvidencePage() {
  const { t } = useI18n();
  const { caseId } = useParams();
  const id = Number(caseId);
  const [searchParams] = useSearchParams();
  const jobFilter = searchParams.get("job_id");
  const sourceFilter = searchParams.get("source_name");
  const entityFilter = searchParams.get("entity_id");
  const { apiKey } = useApiAuth();
  const { caseData } = useOutletContext<CaseOutletContext>();
  const [rows, setRows] = useState<EvidenceSummary[]>([]);
  const [detail, setDetail] = useState<EvidenceDetail | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [detailLoading, setDetailLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [checkingId, setCheckingId] = useState<number | null>(null);
  const [detailPanelOpen, setDetailPanelOpen] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoadState("loading");
    setDetail(null);
    const params: { job_id?: number; source_name?: string; entity_id?: number } = {};
    if (jobFilter) params.job_id = Number(jobFilter);
    if (sourceFilter) params.source_name = sourceFilter;
    if (entityFilter) params.entity_id = Number(entityFilter);
    listCaseEvidence(id, apiKey, params)
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
  }, [apiKey, id, jobFilter, sourceFilter, entityFilter]);

  const isUrlEvidence = (r: EvidenceSummary) =>
    r.source_name === "wayback" ||
    r.finding_kind === "archived_url" ||
    r.evidence_type === "url";

  const checkEvidenceUrl = async (row: EvidenceSummary) => {
    const url = row.finding_value || row.source_url;
    if (!id || !url) return;
    setCheckingId(row.id);
    try {
      await postUrlChecks(id, apiKey, {
        entries: [
          {
            url,
            entity_id: row.entity_id,
            evidence_id: row.id,
          },
        ],
      });
      const refreshed = await getEvidence(row.id, apiKey);
      setDetail(refreshed);
      const params: { job_id?: number; source_name?: string; entity_id?: number } = {};
      if (jobFilter) params.job_id = Number(jobFilter);
      if (sourceFilter) params.source_name = sourceFilter;
      if (entityFilter) params.entity_id = Number(entityFilter);
      setRows(await listCaseEvidence(id, apiKey, params));
    } finally {
      setCheckingId(null);
    }
  };

  const openDetail = (evidenceId: number) => {
    setDetailPanelOpen(true);
    setDetailLoading(true);
    getEvidence(evidenceId, apiKey)
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setDetailLoading(false));
  };

  if (loadState === "loading") return <LoadingBlock label={t("evidence_loading")} />;

  if (loadState === "error") {
    return (
      <EmptyState title={t("evidence_error_title")} description={errorMessage}>
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
      <EmptyState title={t("evidence_empty_title")} description={t("evidence_empty")}>
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
    <div className="space-y-4">
      <p className="text-sm text-slate-500 dark:text-slate-400">{t("evidence_intro")}</p>
      <p className="text-xs text-amber-700 dark:text-amber-300">{t("evidence_no_secrets")}</p>
      <p className="text-xs text-amber-700 dark:text-amber-300">{t("live_check_warning")}</p>

      <div
        className={`grid gap-4 ${
          detail && detailPanelOpen
            ? "lg:grid-cols-[minmax(0,2fr)_minmax(360px,1fr)]"
            : "grid-cols-1"
        }`}
      >
        <DataTableShell minWidth={1200}>
          <thead className="sticky top-0 z-10 border-b border-slate-200 bg-white text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900">
            <tr>
              <th className="px-3 py-2">{t("col_tool")}</th>
              <th className="px-3 py-2">{t("evidence_type")}</th>
              <th className="min-w-[22rem] px-3 py-2">{t("col_value")}</th>
              <th className="px-3 py-2">{t("evidence_hash")}</th>
              <th className="px-3 py-2">{t("live_check_col")}</th>
              <th className="min-w-[12rem] px-3 py-2">{t("data_col_actions")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-slate-100 dark:border-slate-800">
                <td className="px-3 py-2">{r.source_name}</td>
                <td className="px-3 py-2 text-xs">{r.evidence_type}</td>
                <td className="px-3 py-2 align-top">
                  {r.finding_value ? (
                    <DataValueCell
                      value={r.finding_value}
                      badges={
                        r.entity_id ? (
                          <Link
                            to={`/cases/${id}/data?entity_id=${r.entity_id}`}
                            className="text-xs text-slate-400 hover:underline"
                          >
                            #{r.entity_id}
                          </Link>
                        ) : null
                      }
                    />
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-3 py-2 font-mono text-xs" title={r.content_hash_sha256}>
                  …{r.hash_short}
                </td>
                <td className="px-3 py-2">
                  {isUrlEvidence(r) ? (
                    <LiveStatusBadge
                      status={r.live_check?.status ?? "not_checked"}
                      statusCode={r.live_check?.status_code}
                    />
                  ) : (
                    <span className="text-xs text-slate-400">—</span>
                  )}
                </td>
                <td className="px-3 py-2 align-top">
                  <RowActionMenu
                    primary={[
                      {
                        key: "detail",
                        label: t("evidence_view_detail"),
                        onClick: () => openDetail(r.id),
                      },
                      ...(isUrlEvidence(r)
                        ? [
                            {
                              key: "check",
                              label:
                                checkingId === r.id
                                  ? t("live_check_running")
                                  : t("evidence_live_check_btn"),
                              onClick: () => checkEvidenceUrl(r),
                              disabled: checkingId === r.id,
                              className: "text-amber-700 dark:text-amber-400",
                            },
                          ]
                        : []),
                    ]}
                    secondary={
                      r.live_check?.status === "not_found" && r.entity_id
                        ? [
                            {
                              key: "discard404",
                              label: t("evidence_discard_404"),
                              onClick: () =>
                                bulkCaseReview(id, apiKey, {
                                  entity_ids: [r.entity_id!],
                                  hidden: true,
                                  review_status: "discarded",
                                  hidden_reason: "404 not found",
                                }),
                              className: "text-red-600",
                            },
                          ]
                        : []
                    }
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </DataTableShell>

        {detail && detailPanelOpen ? (
        <aside className="min-h-0 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 lg:max-h-[calc(100vh-12rem)] lg:overflow-y-auto">
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-semibold">{t("evidence_detail_title")}</h3>
            <button
              type="button"
              onClick={() => setDetailPanelOpen(false)}
              className="shrink-0 rounded border px-2 py-0.5 text-xs dark:border-slate-700"
            >
              {t("evidence_close_detail")}
            </button>
          </div>
          {detailLoading ? <LoadingBlock /> : null}
          {detail ? (
            <dl className="mt-3 space-y-2 text-sm">
              <div>
                <dt className="text-xs text-slate-500">{t("evidence_hash")}</dt>
                <dd className="break-all font-mono text-xs">{detail.content_hash_sha256}</dd>
                <p className="mt-1 text-xs text-slate-400">{t("evidence_hash_help")}</p>
              </div>
              <div>
                <dt className="text-xs text-slate-500">{t("col_tool")}</dt>
                <dd>{detail.source_name}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">{t("evidence_type")}</dt>
                <dd>{detail.evidence_type}</dd>
              </div>
              {detail.entity_id ? (
                <div>
                  <dt className="text-xs text-slate-500">{t("evidence_entity")}</dt>
                  <dd>
                    <Link
                      to={`/cases/${id}/entities`}
                      className="text-sky-600 hover:underline dark:text-sky-400"
                    >
                      #{detail.entity_id}
                    </Link>
                  </dd>
                </div>
              ) : null}
              {detail.live_check ? (
                <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                  <p className="text-xs font-medium text-slate-500">{t("evidence_live_detail")}</p>
                  <div className="mt-2">
                    <LiveStatusBadge
                      status={detail.live_check.status}
                      statusCode={detail.live_check.status_code}
                    />
                  </div>
                  <dl className="mt-2 grid gap-1 text-xs">
                    {detail.live_check.final_url ? (
                      <div>
                        <dt className="text-slate-500">final_url</dt>
                        <dd className="break-all">{detail.live_check.final_url}</dd>
                      </div>
                    ) : null}
                    {detail.live_check.content_type ? (
                      <div>
                        <dt className="text-slate-500">content_type</dt>
                        <dd>{detail.live_check.content_type}</dd>
                      </div>
                    ) : null}
                    {detail.live_check.content_length != null ? (
                      <div>
                        <dt className="text-slate-500">content_length</dt>
                        <dd>{detail.live_check.content_length}</dd>
                      </div>
                    ) : null}
                    {detail.live_check.checked_at ? (
                      <div>
                        <dt className="text-slate-500">checked_at</dt>
                        <dd>{new Date(detail.live_check.checked_at).toLocaleString()}</dd>
                      </div>
                    ) : null}
                    {detail.live_check.latency_ms != null ? (
                      <div>
                        <dt className="text-slate-500">latency_ms</dt>
                        <dd>{detail.live_check.latency_ms}</dd>
                      </div>
                    ) : null}
                  </dl>
                  {isUrlEvidence(detail) ? (
                    <button
                      type="button"
                      disabled={checkingId === detail.id}
                      onClick={() => checkEvidenceUrl(detail)}
                      className="mt-2 text-xs text-amber-700 hover:underline dark:text-amber-400"
                    >
                      {checkingId === detail.id ? t("live_check_running") : t("evidence_live_check_btn")}
                    </button>
                  ) : null}
                </div>
              ) : isUrlEvidence(detail) ? (
                <div>
                  <p className="text-xs text-slate-500">{t("evidence_live_status")}</p>
                  <LiveStatusBadge status="not_checked" />
                  <button
                    type="button"
                    disabled={checkingId === detail.id}
                    onClick={() => checkEvidenceUrl(detail)}
                    className="mt-2 text-xs text-amber-700 hover:underline dark:text-amber-400"
                  >
                    {checkingId === detail.id ? t("live_check_running") : t("evidence_live_check_btn")}
                  </button>
                </div>
              ) : null}
              {detail.redacted || detail.sensitive ? (
                <p className="text-xs text-amber-700 dark:text-amber-300">
                  {detail.redacted ? t("evidence_redacted_notice") : t("evidence_sensitive_notice")}
                </p>
              ) : null}
              {detail.raw_json ? (
                <details className="mt-2" open>
                  <summary className="cursor-pointer text-xs text-sky-600 dark:text-sky-400">
                    {t("evidence_raw_json")}
                  </summary>
                  <pre className="mt-2 max-h-80 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-200">
                    {detail.raw_json}
                  </pre>
                </details>
              ) : detail.source_url ? (
                <div>
                  <dt className="text-xs text-slate-500">URL</dt>
                  <dd className="break-all text-xs">{detail.source_url}</dd>
                </div>
              ) : (
                <p className="text-xs text-slate-400">{t("evidence_no_raw")}</p>
              )}
            </dl>
          ) : null}
        </aside>
        ) : detail ? (
          <button
            type="button"
            onClick={() => setDetailPanelOpen(true)}
            className="justify-self-start rounded-lg border px-3 py-1.5 text-sm dark:border-slate-700"
          >
            {t("evidence_show_detail")}
          </button>
        ) : null}
      </div>
      {(caseData.jobs_count ?? 0) === 0 ? (
        <p className="text-xs text-slate-400">{t("evidence_no_scans_hint")}</p>
      ) : null}
    </div>
  );
}
