import { useEffect, useMemo, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import { ApiError, listCaseEntities } from "../../api";
import { EmptyState } from "../../components/EmptyState";
import { LoadingBlock } from "../../components/LoadingBlock";
import { QualityBadge } from "../../components/QualityBadge";
import { useApiAuth } from "../../context/ApiAuthContext";
import { useI18n } from "../../i18n";
import type { CaseOutletContext } from "./CaseDetail";
import type { Entity } from "../../types";

type LoadState = "loading" | "ok" | "empty" | "error";

export function CaseEntitiesPage() {
  const { t } = useI18n();
  const { caseId } = useParams();
  const id = Number(caseId);
  const { apiKey } = useApiAuth();
  const { caseData } = useOutletContext<CaseOutletContext>();
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [hideFp, setHideFp] = useState(false);
  const [verifiedOnly, setVerifiedOnly] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoadState("loading");
    listCaseEntities(id, apiKey)
      .then((rows) => {
        setEntities(rows);
        setLoadState(rows.length === 0 ? "empty" : "ok");
      })
      .catch((e: unknown) => {
        setEntities([]);
        setLoadState("error");
        if (e instanceof ApiError) {
          setErrorMessage(e.message ? `Error ${e.status}: ${e.message}` : `Error ${e.status}`);
        } else {
          setErrorMessage(String(e));
        }
      });
  }, [apiKey, id]);

  const filtered = useMemo(() => {
    return entities.filter((e) => {
      if (hideFp && e.is_potential_false_positive) return false;
      if (verifiedOnly) {
        return e.quality_label === "verified" || e.quality_label === "likely";
      }
      return true;
    });
  }, [entities, hideFp, verifiedOnly]);

  if (loadState === "loading") {
    return <LoadingBlock />;
  }

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
      <EmptyState
        title={t("entities_empty_title")}
        description={
          (caseData.jobs_count ?? 0) === 0
            ? t("entities_empty_no_scans")
            : t("entities_empty")
        }
      >
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
    <div className="space-y-3">
      <p className="text-sm text-slate-500 dark:text-slate-400">{t("entities_intro")}</p>
      <div className="flex flex-wrap gap-4 text-sm">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={hideFp} onChange={(e) => setHideFp(e.target.checked)} />
          {t("quality_filter_hide_fp")}
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={verifiedOnly}
            onChange={(e) => setVerifiedOnly(e.target.checked)}
          />
          {t("quality_filter_verified")}
        </label>
      </div>
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800">
            <tr>
              <th className="px-4 py-2">{t("col_kind")}</th>
              <th className="px-4 py-2">{t("col_value")}</th>
              <th className="px-4 py-2">{t("quality_col")}</th>
              <th className="px-4 py-2">{t("entity_last_seen")}</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((e) => (
              <tr key={e.id} className="border-b border-slate-100 dark:border-slate-800">
                <td className="px-4 py-2 font-mono text-xs">{e.entity_type}</td>
                <td className="px-4 py-2">{e.display_value}</td>
                <td className="px-4 py-2">
                  <QualityBadge label={e.quality_label} reason={e.quality_reason} />
                </td>
                <td className="px-4 py-2 text-xs text-slate-500">
                  {new Date(e.last_seen_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {filtered.length === 0 && entities.length > 0 ? (
        <p className="text-sm text-slate-500">{t("no_findings")}</p>
      ) : null}
    </div>
  );
}
