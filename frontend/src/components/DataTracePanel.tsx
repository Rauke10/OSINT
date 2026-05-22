import { useEffect, useState } from "react";
import { ApiError, getEntityTrace } from "../api";
import { useI18n } from "../i18n";
import type { EntityTrace } from "../types";
import { LiveStatusBadge } from "./LiveStatusBadge";
import { QualityBadge } from "./QualityBadge";

export function DataTracePanel({
  entityId,
  apiKey,
  onClose,
}: {
  entityId: number;
  apiKey: string;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const [trace, setTrace] = useState<EntityTrace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    getEntityTrace(entityId, apiKey)
      .then(setTrace)
      .catch((e: unknown) => {
        setTrace(null);
        setError(e instanceof ApiError ? e.message : String(e));
      })
      .finally(() => setLoading(false));
  }, [entityId, apiKey]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-slate-200 bg-white p-4 shadow-xl dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-lg font-semibold">{t("trace_title")}</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded border px-2 py-0.5 text-sm dark:border-slate-600"
          >
            {t("trace_close")}
          </button>
        </div>
        {loading ? <p className="mt-4 text-sm text-slate-500">{t("trace_loading")}</p> : null}
        {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}
        {trace && !loading ? (
          <dl className="mt-4 space-y-3 text-sm">
            <div>
              <dt className="text-xs font-medium text-slate-500">{t("trace_visible")}</dt>
              <dd className="break-all font-mono text-xs">{trace.display_value}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-slate-500">{t("trace_normalized")}</dt>
              <dd className="break-all font-mono text-xs">{trace.normalized_value}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-slate-500">{t("trace_originals")}</dt>
              <dd>
                <ul className="list-inside list-disc font-mono text-xs">
                  {trace.original_values.map((v) => (
                    <li key={v} className="break-all">
                      {v}
                    </li>
                  ))}
                </ul>
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-slate-500">{t("col_source")}</dt>
              <dd>{trace.sources.join(", ") || "—"}</dd>
            </div>
            {trace.quality?.label ? (
              <div>
                <dt className="text-xs font-medium text-slate-500">{t("quality_col")}</dt>
                <dd>
                  <QualityBadge label={trace.quality.label} reason={trace.quality.reason} />
                </dd>
              </div>
            ) : null}
            {trace.group ? (
              <div>
                <dt className="text-xs font-medium text-slate-500">{t("trace_group")}</dt>
                <dd>
                  {trace.group.category} ({trace.group.priority})
                  <p className="mt-1 text-xs text-slate-500">{trace.group.reason}</p>
                  <p className="text-xs text-violet-600 dark:text-violet-400">{t("trace_group_nd")}</p>
                </dd>
              </div>
            ) : null}
            <div>
              <dt className="text-xs font-medium text-slate-500">{t("trace_norm_reason")}</dt>
              <dd className="text-xs">{trace.normalization.reason}</dd>
              {trace.normalization.canonical_key ? (
                <p className="mt-1 font-mono text-xs text-slate-400">
                  canonical: {trace.normalization.canonical_key}
                </p>
              ) : null}
              {trace.normalization.variant_of ? (
                <p className="text-xs text-amber-700">
                  {t("trace_variant_of")} #{trace.normalization.variant_of}
                </p>
              ) : null}
            </div>
            {trace.live_check?.status ? (
              <div>
                <dt className="text-xs font-medium text-slate-500">{t("live_check_col")}</dt>
                <dd>
                  <LiveStatusBadge
                    status={trace.live_check.status}
                    statusCode={trace.live_check.status_code ?? undefined}
                  />
                </dd>
              </div>
            ) : null}
            <div>
              <dt className="text-xs font-medium text-slate-500">{t("trace_evidence_ids")}</dt>
              <dd className="font-mono text-xs">
                {trace.evidence_ids.length ? trace.evidence_ids.join(", ") : "—"}
              </dd>
            </div>
            {trace.review?.hidden ? (
              <div>
                <dt className="text-xs font-medium text-slate-500">{t("ops_discarded")}</dt>
                <dd className="text-xs">{trace.review.hidden_reason ?? trace.review.review_status}</dd>
              </div>
            ) : null}
          </dl>
        ) : null}
      </div>
    </div>
  );
}
