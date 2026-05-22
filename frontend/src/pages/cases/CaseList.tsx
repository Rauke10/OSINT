import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, deleteCase, listCases, updateCase } from "../../api";
import { ApiKeyPanel } from "../../components/ApiKeyPanel";
import { EmptyState } from "../../components/EmptyState";
import { LoadingBlock } from "../../components/LoadingBlock";
import { useApiAuth } from "../../context/ApiAuthContext";
import { useI18n } from "../../i18n";
import type { Case } from "../../types";

type LoadState = "idle" | "loading" | "ok" | "empty" | "error" | "no_key";

export function CaseListPage() {
  const { t } = useI18n();
  const { apiKey, requiresApiKey } = useApiAuth();
  const [cases, setCases] = useState<Case[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Case | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  const reload = () => {
    if (requiresApiKey && !apiKey) {
      setCases([]);
      setLoadState("no_key");
      return;
    }
    setLoadState("loading");
    listCases(apiKey, includeArchived)
      .then((rows) => {
        setCases(rows);
        setLoadState(rows.length === 0 ? "empty" : "ok");
      })
      .catch((e: unknown) => {
        setCases([]);
        setLoadState("error");
        if (e instanceof ApiError) {
          setErrorMessage(
            e.message ? `Error ${e.status}: ${e.message}` : `Error ${e.status}`,
          );
        } else {
          setErrorMessage(String(e));
        }
      });
  };

  useEffect(() => {
    reload();
  }, [apiKey, requiresApiKey, includeArchived]);

  const archiveCase = async (c: Case) => {
    setBusyId(c.id);
    try {
      await updateCase(c.id, { status: "archived" }, apiKey);
      reload();
    } finally {
      setBusyId(null);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget || deleteConfirm !== "BORRAR") return;
    setBusyId(deleteTarget.id);
    try {
      await deleteCase(deleteTarget.id, apiKey);
      setDeleteTarget(null);
      setDeleteConfirm("");
      reload();
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">{t("nav_cases")}</h1>
        <Link
          to="/cases/new"
          className="rounded-lg bg-sky-600 px-3 py-2 text-sm text-white hover:bg-sky-500"
        >
          {t("case_new")}
        </Link>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={includeArchived}
          onChange={(e) => setIncludeArchived(e.target.checked)}
        />
        {t("cases_show_archived")}
      </label>

      {loadState === "no_key" ? <ApiKeyPanel /> : null}

      {loadState === "loading" ? <LoadingBlock /> : null}

      {loadState === "error" ? (
        <EmptyState title={t("state_backend_error")} description={errorMessage} />
      ) : null}

      {loadState === "empty" ? (
        <EmptyState title={t("cases_empty_title")} description={t("cases_empty")}>
          <Link
            to="/cases/new"
            className="rounded-lg bg-sky-600 px-3 py-2 text-sm text-white hover:bg-sky-500"
          >
            {t("case_new")}
          </Link>
        </EmptyState>
      ) : null}

      {loadState === "ok" ? (
        <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
          {cases.map((c) => (
            <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
              <div>
                <Link
                  to={`/cases/${c.id}/search`}
                  className="font-medium text-sky-600 hover:underline dark:text-sky-400"
                >
                  {c.title}
                </Link>
                <p className="text-xs text-slate-500">
                  {c.status} · {c.jobs_count ?? 0} {t("dash_total_jobs")} ·{" "}
                  {c.entities_count ?? 0} {t("dash_entities")}
                </p>
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                {c.status !== "archived" ? (
                  <button
                    type="button"
                    disabled={busyId === c.id}
                    onClick={() => archiveCase(c)}
                    className="rounded border px-2 py-1 dark:border-slate-700"
                  >
                    {t("case_archive")}
                  </button>
                ) : null}
                <button
                  type="button"
                  disabled={busyId === c.id}
                  onClick={() => {
                    setDeleteTarget(c);
                    setDeleteConfirm("");
                  }}
                  className="rounded border border-red-300 px-2 py-1 text-red-700 dark:border-red-800"
                >
                  {t("case_delete")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      {deleteTarget ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-w-md rounded-xl border border-slate-200 bg-white p-4 shadow-lg dark:border-slate-700 dark:bg-slate-900">
            <h3 className="font-semibold text-red-700">{t("case_delete_confirm_title")}</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
              {t("case_delete_confirm_body").replace("{title}", deleteTarget.title)}
            </p>
            <p className="mt-2 text-xs text-slate-500">{t("case_delete_type_confirm")}</p>
            <input
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
              className="mt-2 w-full rounded border px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
              placeholder="BORRAR"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                className="rounded border px-3 py-1 text-sm dark:border-slate-700"
              >
                {t("cancel")}
              </button>
              <button
                type="button"
                disabled={deleteConfirm !== "BORRAR" || busyId === deleteTarget.id}
                onClick={() => void confirmDelete()}
                className="rounded bg-red-600 px-3 py-1 text-sm text-white disabled:opacity-50"
              >
                {t("case_delete")}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
