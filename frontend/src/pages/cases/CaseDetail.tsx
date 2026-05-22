import { useCallback, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useOutletContext, useParams } from "react-router-dom";
import { ApiError, getCase } from "../../api";
import { ApiKeyPanel } from "../../components/ApiKeyPanel";
import { LoadingBlock } from "../../components/LoadingBlock";
import { useApiAuth } from "../../context/ApiAuthContext";
import { useI18n } from "../../i18n";
import type { Case } from "../../types";

const tabClass = ({ isActive }: { isActive: boolean }) =>
  `shrink-0 rounded-lg px-3 py-1.5 text-sm ${
    isActive
      ? "bg-sky-600 text-white"
      : "border border-slate-300 dark:border-slate-700"
  }`;

export type CaseOutletContext = {
  caseData: Case;
  apiKey: string;
  refreshKey: number;
  bumpRefresh: () => void;
};

type FetchStatus =
  | "idle"
  | "loading"
  | "ok"
  | "not_found"
  | "error"
  | "no_api_key"
  | "invalid_id";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function CaseDetailPage() {
  const { t } = useI18n();
  const { caseId: caseIdParam } = useParams();
  const parsedId = caseIdParam ? Number(caseIdParam) : Number.NaN;
  const validId = Number.isFinite(parsedId) && parsedId > 0;
  const id = validId ? parsedId : 0;
  const { apiKey, requiresApiKey } = useApiAuth();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [status, setStatus] = useState<FetchStatus>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const bumpRefresh = useCallback(() => setRefreshKey((k) => k + 1), []);
  const outletCtx = (data: Case): CaseOutletContext => ({
    caseData: data,
    apiKey,
    refreshKey,
    bumpRefresh,
  });

  useEffect(() => {
    if (!validId) {
      setStatus("invalid_id");
      setCaseData(null);
      return;
    }

    if (requiresApiKey && !apiKey) {
      setStatus("no_api_key");
      setCaseData(null);
      return;
    }

    let cancelled = false;
    setStatus("loading");
    setCaseData(null);
    setErrorMessage("");

    getCase(parsedId, apiKey)
      .then((data) => {
        if (cancelled) return;
        setCaseData(data);
        setStatus("ok");
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setCaseData(null);
        if (e instanceof ApiError) {
          if (e.status === 404) {
            setStatus("not_found");
            return;
          }
          if (e.status === 401) {
            setStatus("error");
            setErrorMessage(t("err_401"));
            return;
          }
          setStatus("error");
          setErrorMessage(
            e.message ? `Error ${e.status}: ${e.message}` : `Error ${e.status}`,
          );
          return;
        }
        setStatus("error");
        setErrorMessage(`${t("err_network")}: ${String(e)}`);
      });

    return () => {
      cancelled = true;
    };
  }, [apiKey, parsedId, requiresApiKey, validId, t]);

  if (status === "invalid_id") {
    return (
      <div className="space-y-3">
        <p className="text-sm text-red-600 dark:text-red-400">{t("case_invalid_id")}</p>
        <Link
          to="/cases"
          className="inline-block rounded-lg bg-sky-600 px-3 py-2 text-sm text-white hover:bg-sky-500"
        >
          {t("case_back_to_list")}
        </Link>
      </div>
    );
  }

  if (status === "no_api_key") {
    const base = `/cases/${parsedId}`;
    const stub: Case = {
      id: parsedId,
      title: t("case_untitled_placeholder"),
      description: null,
      status: "open",
      reference_code: null,
      created_at: "",
      updated_at: "",
      targets_count: 0,
      jobs_count: 0,
      entities_count: 0,
    };
    return (
      <div className="space-y-4">
        <div>
          <Link to="/cases" className="text-xs text-sky-600 hover:underline dark:text-sky-400">
            ← {t("nav_cases")}
          </Link>
          <h1 className="mt-1 text-xl font-bold">{stub.title}</h1>
        </div>
        <ApiKeyPanel />
        <nav className="-mx-1 flex gap-2 overflow-x-auto pb-1">
          <NavLink to={`${base}/search`} className={tabClass}>
            {t("case_search")}
          </NavLink>
          <NavLink to={`${base}/data`} className={tabClass}>
            {t("case_raw_data")}
          </NavLink>
          <NavLink to={`${base}/inventory`} className={tabClass}>
            {t("case_inventory")}
          </NavLink>
          <NavLink to={`${base}/sources`} className={tabClass}>
            {t("case_sources")}
          </NavLink>
          <NavLink to={`${base}/graph`} className={tabClass}>
            {t("graph_case_title")}
          </NavLink>
          <NavLink to={`${base}/reports`} className={tabClass}>
            {t("case_reports")}
          </NavLink>
        </nav>
        <Outlet context={outletCtx(stub)} />
      </div>
    );
  }

  if (status === "loading" || status === "idle") {
    return <LoadingBlock label={t("case_loading")} />;
  }

  if (status === "not_found") {
    return (
      <div className="space-y-3">
        <p className="text-sm text-slate-600 dark:text-slate-400">{t("case_not_found")}</p>
        <Link
          to="/cases"
          className="inline-block rounded-lg bg-sky-600 px-3 py-2 text-sm text-white hover:bg-sky-500"
        >
          {t("case_back_to_list")}
        </Link>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="space-y-3">
        <p className="text-sm text-red-600 dark:text-red-400">
          {errorMessage || t("case_load_error")}
        </p>
        <Link
          to="/cases"
          className="inline-block rounded-lg border border-slate-300 px-3 py-2 text-sm hover:border-sky-500 dark:border-slate-700"
        >
          {t("case_back_to_list")}
        </Link>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-red-600 dark:text-red-400">{t("case_load_error")}</p>
        <Link to="/cases" className="text-sm text-sky-600 hover:underline dark:text-sky-400">
          {t("case_back_to_list")}
        </Link>
      </div>
    );
  }

  const base = `/cases/${id}`;

  return (
    <div className="space-y-4">
      <div>
        <Link to="/cases" className="text-xs text-sky-600 hover:underline dark:text-sky-400">
          ← {t("nav_cases")}
        </Link>
        <h1 className="mt-1 text-xl font-bold">{caseData.title}</h1>
        {caseData.description ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">{caseData.description}</p>
        ) : null}
        <dl className="mt-2 grid gap-1 text-xs text-slate-500 dark:text-slate-400 sm:grid-cols-2">
          <div>
            <dt className="inline font-medium">{t("case_meta_status")}: </dt>
            <dd className="inline">{caseData.status}</dd>
          </div>
          {caseData.reference_code ? (
            <div>
              <dt className="inline font-medium">{t("case_meta_reference")}: </dt>
              <dd className="inline font-mono">{caseData.reference_code}</dd>
            </div>
          ) : null}
          <div>
            <dt className="inline font-medium">{t("case_meta_created")}: </dt>
            <dd className="inline">{formatDate(caseData.created_at)}</dd>
          </div>
          <div>
            <dt className="inline font-medium">{t("case_meta_updated")}: </dt>
            <dd className="inline">{formatDate(caseData.updated_at)}</dd>
          </div>
          <div>
            <dt className="inline font-medium">{t("case_meta_targets")}: </dt>
            <dd className="inline">{caseData.targets_count ?? 0}</dd>
          </div>
          <div>
            <dt className="inline font-medium">{t("case_meta_jobs")}: </dt>
            <dd className="inline">{caseData.jobs_count ?? 0}</dd>
          </div>
          <div>
            <dt className="inline font-medium">{t("case_meta_entities")}: </dt>
            <dd className="inline">{caseData.entities_count ?? 0}</dd>
          </div>
        </dl>
      </div>
      <nav className="-mx-1 flex gap-2 overflow-x-auto pb-1">
        <NavLink to={`${base}/search`} className={tabClass}>
          {t("case_search")}
        </NavLink>
        <NavLink to={`${base}/data`} className={tabClass}>
          {t("case_raw_data")}
        </NavLink>
        <NavLink to={`${base}/inventory`} className={tabClass}>
          {t("case_inventory")}
        </NavLink>
        <NavLink to={`${base}/sources`} className={tabClass}>
          {t("case_sources")}
        </NavLink>
        <NavLink to={`${base}/graph`} className={tabClass}>
          {t("graph_case_title")}
        </NavLink>
        <NavLink to={`${base}/reports`} className={tabClass}>
          {t("case_reports")}
        </NavLink>
      </nav>
      <Outlet context={outletCtx(caseData)} />
    </div>
  );
}

export function CaseOverviewTab() {
  const { t } = useI18n();
  const { caseData } = useOutletContext<CaseOutletContext>();
  const id = caseData.id;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm dark:border-slate-800 dark:bg-slate-900">
      <p>{t("case_overview_hint")}</p>
      <Link
        to={`/cases/${id}/search`}
        className="mt-3 inline-block text-sky-600 hover:underline dark:text-sky-400"
      >
        {t("case_search")} →
      </Link>
    </div>
  );
}
