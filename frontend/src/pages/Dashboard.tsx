import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, listCases } from "../api";
import { ApiKeyPanel } from "../components/ApiKeyPanel";
import { EmptyState } from "../components/EmptyState";
import { LoadingBlock } from "../components/LoadingBlock";
import { useApiAuth } from "../context/ApiAuthContext";
import { useI18n } from "../i18n";
import type { Case } from "../types";

type LoadState = "idle" | "loading" | "ok" | "empty" | "error" | "no_key";

export function DashboardPage() {
  const { t } = useI18n();
  const { apiKey, requiresApiKey } = useApiAuth();
  const [cases, setCases] = useState<Case[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (requiresApiKey && !apiKey) {
      setCases([]);
      setLoadState("no_key");
      return;
    }
    setLoadState("loading");
    listCases(apiKey)
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
  }, [apiKey, requiresApiKey]);

  const open = cases.filter((c) => c.status === "open");
  const entities = cases.reduce((n, c) => n + (c.entities_count ?? 0), 0);
  const jobs = cases.reduce((n, c) => n + (c.jobs_count ?? 0), 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">{t("nav_dashboard")}</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">{t("dashboard_intro")}</p>
      </div>

      {loadState === "no_key" ? (
        <ApiKeyPanel />
      ) : null}

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
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
              <div className="text-2xl font-bold">{open.length}</div>
              <div className="text-xs text-slate-500">{t("dash_open_cases")}</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
              <div className="text-2xl font-bold">{jobs}</div>
              <div className="text-xs text-slate-500">{t("dash_total_jobs")}</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
              <div className="text-2xl font-bold">{entities}</div>
              <div className="text-xs text-slate-500">{t("dash_entities")}</div>
            </div>
          </div>

          <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold">{t("nav_cases")}</h2>
              <Link
                to="/cases/new"
                className="rounded-lg bg-sky-600 px-3 py-1.5 text-sm text-white hover:bg-sky-500"
              >
                {t("case_new")}
              </Link>
            </div>
            <ul className="space-y-2">
              {cases.slice(0, 8).map((c) => (
                <li key={c.id}>
                  <Link
                    to={`/cases/${c.id}/search`}
                    className="text-sm font-medium text-sky-600 hover:underline dark:text-sky-400"
                  >
                    {c.title}
                  </Link>
                  <span className="ml-2 text-xs text-slate-400">
                    {c.entities_count ?? 0} {t("dash_entities")}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </>
      ) : null}
    </div>
  );
}
