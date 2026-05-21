import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  fetchReport,
  getHistory,
  getHistoryItem,
  getSources,
  runScan,
} from "./api";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Header } from "./components/Header";
import { ScanForm } from "./components/ScanForm";
import { SourcesPanel } from "./components/SourcesPanel";
import { RelationshipGraph } from "./components/RelationshipGraph";
import { FindingsTable } from "./components/FindingsTable";
import { HistoryPanel } from "./components/HistoryPanel";
import { useI18n } from "./i18n";
import type { HistoryItem, ScanResult, SourceInfo } from "./types";

type Theme = "dark" | "light";

const cardAccent: Record<string, string> = {
  total: "",
  high: "text-red-500",
  medium: "text-amber-500",
  low: "text-emerald-500",
};

const KEY_STORE = "globeye-key";
const REMEMBER_STORE = "globeye-remember";

/** The API key lives in sessionStorage by default; localStorage if "remember". */
function loadStoredKey(): { key: string; remember: boolean } {
  try {
    const remember = localStorage.getItem(REMEMBER_STORE) === "1";
    const store = remember ? localStorage : sessionStorage;
    return { key: store.getItem(KEY_STORE) ?? "", remember };
  } catch {
    return { key: "", remember: false };
  }
}

function persistKey(key: string, remember: boolean): void {
  try {
    const [keep, drop] = remember
      ? [localStorage, sessionStorage]
      : [sessionStorage, localStorage];
    keep.setItem(KEY_STORE, key);
    drop.removeItem(KEY_STORE);
    localStorage.setItem(REMEMBER_STORE, remember ? "1" : "0");
  } catch {
    /* ignore */
  }
}

export function App() {
  const { t } = useI18n();
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      return localStorage.getItem("globeye-theme") === "light" ? "light" : "dark";
    } catch {
      return "dark";
    }
  });
  const [apiKey, setApiKey] = useState(() => loadStoredKey().key);
  const [rememberKey, setRememberKey] = useState(() => loadStoredKey().remember);
  const [target, setTarget] = useState("");
  const [pivot, setPivot] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ScanResult | null>(null);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [catalog, setCatalog] = useState<SourceInfo[]>([]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    try {
      localStorage.setItem("globeye-theme", theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  useEffect(() => {
    getSources()
      .then(setCatalog)
      .catch(() => undefined);
  }, []);

  const setKey = (k: string) => {
    setApiKey(k);
    persistKey(k, rememberKey);
  };

  const setRemember = (remember: boolean) => {
    setRememberKey(remember);
    persistKey(apiKey, remember);
  };

  const describeError = useCallback(
    (e: unknown): string => {
      if (e instanceof ApiError) {
        if (e.status === 401) return t("err_401");
        if (e.status === 503) return t("err_503");
        return `Error ${e.status}${e.message ? `: ${e.message}` : ""}`;
      }
      return `${t("err_network")}: ${String(e)}`;
    },
    [t],
  );

  const loadHistory = useCallback(() => {
    if (!apiKey) {
      setHistory([]);
      return;
    }
    getHistory(apiKey)
      .then(setHistory)
      .catch(() => setHistory([]));
  }, [apiKey]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const onScan = async () => {
    setError("");
    if (!target.trim()) {
      setError(t("err_empty"));
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const r = await runScan(target.trim(), pivot, apiKey);
      setResult(r);
      setCurrentId(r.scan_id ?? null);
      loadHistory();
    } catch (e) {
      setError(describeError(e));
    } finally {
      setLoading(false);
    }
  };

  const openHistory = async (item: HistoryItem) => {
    setError("");
    try {
      const r = await getHistoryItem(item.id, apiKey);
      setResult(r);
      setCurrentId(item.id);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setError(describeError(e));
    }
  };

  const exportJson = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `globeye-${result.target.value || "scan"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const openReport = async () => {
    if (currentId == null) return;
    try {
      const blob = await fetchReport(currentId, apiKey);
      window.open(URL.createObjectURL(blob), "_blank", "noopener");
    } catch (e) {
      setError(describeError(e));
    }
  };

  const cards = result
    ? [
        { key: "total", value: result.summary.findings.total },
        { key: "high", value: result.summary.findings.high },
        { key: "medium", value: result.summary.findings.medium },
        { key: "low", value: result.summary.findings.low },
      ]
    : [];

  return (
    <div className="min-h-full bg-slate-100 text-slate-800 dark:bg-slate-950 dark:text-slate-200">
      <Header
        theme={theme}
        onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
      />

      <main className="mx-auto max-w-6xl space-y-6 px-5 py-6">
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-2.5 text-xs text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300">
          ⚠️ {t("legal")}
        </div>

        <ScanForm
          target={target}
          setTarget={setTarget}
          apiKey={apiKey}
          setApiKey={setKey}
          remember={rememberKey}
          setRemember={setRemember}
          pivot={pivot}
          setPivot={setPivot}
          loading={loading}
          error={error}
          onScan={onScan}
        />

        {result ? (
          <div className="space-y-6">
            <section className="flex flex-wrap items-center gap-3">
              {cards.map((c) => (
                <div
                  key={c.key}
                  className="min-w-[96px] rounded-xl border border-slate-200 bg-white px-4 py-2.5 dark:border-slate-800 dark:bg-slate-900"
                >
                  <div
                    className={`text-xl font-bold ${cardAccent[c.key] ?? ""}`}
                  >
                    {c.value}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    {t(`card_${c.key === "total" ? "findings" : c.key}`)}
                  </div>
                </div>
              ))}
              <div className="ml-auto flex gap-2">
                <button
                  type="button"
                  onClick={exportJson}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:border-sky-500 dark:border-slate-700"
                >
                  ⤓ {t("export_json")}
                </button>
                <button
                  type="button"
                  onClick={openReport}
                  disabled={currentId == null}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:border-sky-500 disabled:opacity-40 dark:border-slate-700"
                >
                  ⤓ {t("export_report")}
                </button>
              </div>
            </section>

            <p className="text-sm text-slate-500 dark:text-slate-400">
              {t("target_word")}{" "}
              <code className="font-semibold">{result.target.type}</code>{" "}
              <span className="font-semibold text-slate-700 dark:text-slate-200">
                {result.target.value}
              </span>{" "}
              · {result.summary.duration_seconds}s
              {result.summary.pivoted_targets.length > 0 && (
                <>
                  {" "}
                  · {t("pivoted")}:{" "}
                  {result.summary.pivoted_targets
                    .map((p) => p.value)
                    .join(", ")}
                </>
              )}
            </p>

            <SourcesPanel result={result} catalog={catalog} />
            <ErrorBoundary label="the relationship graph">
              <RelationshipGraph result={result} />
            </ErrorBoundary>
            <ErrorBoundary label="the findings table">
              <FindingsTable findings={result.findings} />
            </ErrorBoundary>
          </div>
        ) : (
          <p className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-10 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
            {t("empty_hint")}
          </p>
        )}

        <HistoryPanel
          history={history}
          onOpen={openHistory}
          onRefresh={loadHistory}
        />
      </main>

      <footer className="mx-auto max-w-6xl px-5 py-6 text-xs text-slate-400 dark:text-slate-600">
        {t("footer")}
      </footer>
    </div>
  );
}
