import { useCallback, useEffect, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import { ApiError, getCaseGraph } from "../../api";
import { EmptyState } from "../../components/EmptyState";
import { LoadingBlock } from "../../components/LoadingBlock";
import { RelationshipGraph } from "../../components/RelationshipGraph";
import { useI18n } from "../../i18n";
import type { CaseOutletContext } from "./CaseDetail";
import type { GraphPayload } from "../../types";

type LoadState = "loading" | "ok" | "empty" | "error";
type GraphMode = "inventory" | "all" | "live" | "high";

export function CaseGraphPage() {
  const { t } = useI18n();
  const { caseId } = useParams();
  const id = Number(caseId);
  const { caseData, apiKey, refreshKey } = useOutletContext<CaseOutletContext>();
  const [mode, setMode] = useState<GraphMode>("inventory");
  const [graph, setGraph] = useState<GraphPayload | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [errorMessage, setErrorMessage] = useState("");

  const load = useCallback(() => {
    if (!id) return;
    setLoadState("loading");
    getCaseGraph(id, apiKey, mode)
      .then((g) => {
        setGraph(g);
        setLoadState(g.nodes.length === 0 ? "empty" : "ok");
      })
      .catch((e: unknown) => {
        setGraph(null);
        setLoadState("error");
        if (e instanceof ApiError) {
          setErrorMessage(e.message ? `Error ${e.status}: ${e.message}` : `Error ${e.status}`);
        } else {
          setErrorMessage(String(e));
        }
      });
  }, [apiKey, id, mode]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  if (loadState === "loading") {
    return <LoadingBlock />;
  }

  if (loadState === "error") {
    return (
      <EmptyState title={t("state_backend_error")} description={errorMessage}>
        <button
          type="button"
          onClick={load}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700"
        >
          {t("refresh")}
        </button>
      </EmptyState>
    );
  }

  if (loadState === "empty") {
    return (
      <div className="space-y-4">
        <GraphModeBar mode={mode} onMode={setMode} />
        <p className="text-sm text-slate-600 dark:text-slate-400">{t("graph_default_inventory_note")}</p>
        <EmptyState
          title={t("graph_empty_title")}
          description={
            mode === "inventory"
              ? t("graph_empty_inventory")
              : (caseData.jobs_count ?? 0) === 0
                ? t("graph_empty_no_scans")
                : t("graph_empty")
          }
        >
          <Link
            to={`/cases/${id}/inventory`}
            className="rounded-lg bg-sky-600 px-3 py-2 text-sm text-white hover:bg-sky-500"
          >
            {t("case_inventory")}
          </Link>
          <Link
            to={`/cases/${id}/data`}
            className="rounded-lg border px-3 py-2 text-sm dark:border-slate-700"
          >
            {t("case_raw_data")}
          </Link>
        </EmptyState>
      </div>
    );
  }

  if (!graph) return null;

  return (
    <div className="space-y-3">
      <GraphModeBar mode={mode} onMode={setMode} />
      <p className="text-sm text-slate-600 dark:text-slate-400">{t("graph_default_inventory_note")}</p>
      <RelationshipGraph
        graph={graph}
        titleKey="graph_case_title"
        subtitleKey={mode === "inventory" ? "graph_case_subtitle_inventory" : "graph_case_subtitle"}
      />
    </div>
  );
}

function GraphModeBar({
  mode,
  onMode,
}: {
  mode: GraphMode;
  onMode: (m: GraphMode) => void;
}) {
  const { t } = useI18n();
  const modes: { id: GraphMode; labelKey: string }[] = [
    { id: "inventory", labelKey: "graph_mode_inventory" },
    { id: "all", labelKey: "graph_mode_all" },
    { id: "live", labelKey: "graph_mode_live" },
    { id: "high", labelKey: "graph_mode_high" },
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {modes.map((m) => (
        <button
          key={m.id}
          type="button"
          onClick={() => onMode(m.id)}
          className={`rounded-lg px-3 py-1.5 text-sm ${
            mode === m.id
              ? "bg-sky-600 text-white"
              : "border border-slate-300 dark:border-slate-700"
          }`}
        >
          {t(m.labelKey)}
        </button>
      ))}
    </div>
  );
}
