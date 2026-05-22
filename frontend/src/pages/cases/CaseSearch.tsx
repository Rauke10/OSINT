import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { ApiError, fetchReport, getSources, previewSourceRouting, runCaseScan } from "../../api";
import { LegalBanner } from "../../components/LegalBanner";
import { PostScanBanner } from "../../components/PostScanBanner";
import { FindingsTable } from "../../components/FindingsTable";
import { RelationshipGraph } from "../../components/RelationshipGraph";
import { ScanForm } from "../../components/ScanForm";
import { SourceRoutingPreviewPanel } from "../../components/SourceRoutingPreview";
import { SourcesPanel } from "../../components/SourcesPanel";
import { useApiAuth } from "../../context/ApiAuthContext";
import { useI18n } from "../../i18n";
import type { ScanDepth, ScanResult, SourceInfo, SourceRoutingPreview } from "../../types";

const DEPTH_OPTIONS: { value: ScanDepth; labelKey: string }[] = [
  { value: "quick", labelKey: "depth_quick" },
  { value: "standard", labelKey: "depth_standard" },
  { value: "deep", labelKey: "depth_deep" },
];

export function CaseSearchPage() {
  const { t } = useI18n();
  const { caseId } = useParams();
  const id = Number(caseId);
  const { apiKey } = useApiAuth();
  const [target, setTarget] = useState("");
  const [pivot, setPivot] = useState(false);
  const [depth, setDepth] = useState<ScanDepth>("standard");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ScanResult | null>(null);
  const [scanId, setScanId] = useState<number | null>(null);
  const [catalog, setCatalog] = useState<SourceInfo[]>([]);
  const [preview, setPreview] = useState<SourceRoutingPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");

  useEffect(() => {
    getSources()
      .then(setCatalog)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const trimmed = target.trim();
    if (trimmed.length < 3) {
      setPreview(null);
      setPreviewError("");
      return;
    }
    const timer = window.setTimeout(() => {
      setPreviewLoading(true);
      setPreviewError("");
      previewSourceRouting(trimmed, depth, apiKey)
        .then(setPreview)
        .catch((e: unknown) => {
          setPreview(null);
          if (e instanceof ApiError) {
            setPreviewError(
              e.message ? `Error ${e.status}: ${e.message}` : `Error ${e.status}`,
            );
          } else {
            setPreviewError(String(e));
          }
        })
        .finally(() => setPreviewLoading(false));
    }, 500);
    return () => window.clearTimeout(timer);
  }, [target, depth, apiKey]);

  const describeError = useCallback(
    (e: unknown): string => {
      if (e instanceof ApiError) {
        if (e.status === 401) return t("err_401");
        return `Error ${e.status}${e.message ? `: ${e.message}` : ""}`;
      }
      return `${t("err_network")}: ${String(e)}`;
    },
    [t],
  );

  const onScan = async () => {
    setError("");
    if (!target.trim()) {
      setError(t("err_empty"));
      return;
    }
    if (depth === "deep" && !window.confirm(t("depth_deep_confirm"))) {
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const r = await runCaseScan(id, target.trim(), pivot, apiKey, depth);
      setResult(r);
      setScanId(r.scan_id ?? null);
      if (r.routing) setPreview(r.routing);
    } catch (e) {
      setError(describeError(e));
    } finally {
      setLoading(false);
    }
  };

  const openReport = async () => {
    if (scanId == null) return;
    try {
      const blob = await fetchReport(scanId, apiKey);
      window.open(URL.createObjectURL(blob), "_blank", "noopener");
    } catch (e) {
      setError(describeError(e));
    }
  };

  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500 dark:text-slate-400">{t("case_search_intro")}</p>
      <LegalBanner />
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
          {t("depth_label")}
        </span>
        {DEPTH_OPTIONS.map((opt) => (
          <label
            key={opt.value}
            className="flex cursor-pointer items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700"
          >
            <input
              type="radio"
              name="depth"
              value={opt.value}
              checked={depth === opt.value}
              onChange={() => setDepth(opt.value)}
            />
            {t(opt.labelKey)}
          </label>
        ))}
      </div>
      <ScanForm
        target={target}
        setTarget={setTarget}
        pivot={pivot}
        setPivot={setPivot}
        loading={loading}
        error={error}
        onScan={onScan}
        scanLabel={t("case_search")}
      />
      <SourceRoutingPreviewPanel
        preview={preview}
        loading={previewLoading}
        error={previewError}
      />
      {result ? (
        <>
          <PostScanBanner caseId={id} />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={openReport}
              disabled={scanId == null}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
            >
              {t("export_report")}
            </button>
          </div>
          <SourcesPanel result={result} catalog={catalog} routing={result.routing} />
          <RelationshipGraph
            result={result}
            titleKey="graph_scan_title"
            subtitleKey="graph_scan_subtitle"
          />
          <FindingsTable findings={result.findings} />
        </>
      ) : null}
    </div>
  );
}
