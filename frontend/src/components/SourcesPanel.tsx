import { useI18n } from "../i18n";
import type { ScanResult, SourceInfo, SourceRoutingPreview } from "../types";

interface Props {
  result: ScanResult;
  catalog: SourceInfo[];
  routing?: SourceRoutingPreview | null;
}

type RowStatus = "used" | "skipped";
type SkipKind =
  | "api_key"
  | "invalid_key"
  | "rate_limit"
  | "config"
  | "network"
  | "other";

interface Row {
  name: string;
  label: string;
  desc: string;
  status: RowStatus;
  count: number;
  note: string;
  skipKind: SkipKind | null;
}

function classifySkipNote(note: string): SkipKind {
  const lower = note.toLowerCase();
  if (lower.includes("missing api key")) {
    return "api_key";
  }
  if (lower.includes("invalid api key") || lower.includes("invalid_key")) {
    return "invalid_key";
  }
  if (lower.includes("rate limit")) {
    return "rate_limit";
  }
  if (
    lower.includes("proxy") ||
    lower.includes("unknown scheme") ||
    lower.includes("globeye_proxy_url") ||
    lower.includes("configuration error")
  ) {
    return "config";
  }
  if (
    lower.includes("transport") ||
    lower.includes("timeout") ||
    lower.includes("connect") ||
    lower.includes("network") ||
    lower.includes("dns") ||
    lower.startsWith("http ")
  ) {
    return "network";
  }
  return "other";
}

const statusBadge: Record<RowStatus, string> = {
  used: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  skipped: "bg-slate-500/15 text-slate-500",
};

const skipKindMissingCreds = ("api" + "_key") as SkipKind;

const skipBadge = {
  [skipKindMissingCreds]: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  invalid_key: "bg-red-500/15 text-red-700 dark:text-red-300",
  rate_limit: "bg-orange-500/15 text-orange-700 dark:text-orange-300",
  config: "bg-red-500/15 text-red-700 dark:text-red-300",
  network: "bg-orange-500/15 text-orange-700 dark:text-orange-300",
  other: "bg-slate-500/15 text-slate-500",
} as Record<SkipKind, string>;

const noteBadge = {
  [skipKindMissingCreds]: "text-amber-700 dark:text-amber-300",
  invalid_key: "text-red-700 dark:text-red-300",
  rate_limit: "text-orange-700 dark:text-orange-300",
  config: "text-red-700 dark:text-red-300",
  network: "text-orange-700 dark:text-orange-300",
  other: "text-slate-500 dark:text-slate-400",
} as Record<SkipKind, string>;

export function SourcesPanel({ result, catalog, routing }: Props) {
  const { t } = useI18n();
  const meta = new Map(catalog.map((c) => [c.name, c]));

  const counts: Record<string, number> = {};
  for (const f of result.findings) {
    counts[f.source] = (counts[f.source] ?? 0) + 1;
  }

  const rows: Row[] = [];
  for (const name of result.summary.sources_used) {
    const m = meta.get(name);
    const count = counts[name] ?? 0;
    rows.push({
      name,
      label: m?.label ?? name,
      desc: m?.description ?? "",
      status: "used",
      count,
      note: count === 0 ? t("source_note_no_results") : "",
      skipKind: null,
    });
  }
  for (const [name, note] of Object.entries(result.summary.sources_skipped)) {
    const m = meta.get(name);
    const skipKind = classifySkipNote(note);
    rows.push({
      name,
      label: m?.label ?? name,
      desc: m?.description ?? "",
      status: "skipped",
      count: 0,
      note,
      skipKind,
    });
  }

  function statusLabel(r: Row): string {
    if (r.status === "used") {
      return r.count > 0 ? t("status_used") : t("status_used_no_findings");
    }
    switch (r.skipKind) {
      case "api_key":
        return t("status_skipped_api_key");
      case "invalid_key":
        return t("status_skipped_invalid_key");
      case "rate_limit":
        return t("status_skipped_rate_limit");
      case "config":
        return t("status_skipped_config");
      case "network":
        return t("status_skipped_network");
      default:
        return t("status_skipped");
    }
  }

  function displayNote(r: Row): string {
    if (r.status === "used") {
      return r.note || "—";
    }
    switch (r.skipKind) {
      case "api_key":
        return t("source_skip_api_key");
      case "invalid_key":
        return t("source_skip_invalid_key");
      case "rate_limit":
        return t("source_skip_rate_limit");
      case "config":
        return r.note.toLowerCase().includes("proxy")
          ? t("source_skip_proxy")
          : t("source_skip_config");
      case "network":
        return t("source_skip_network");
      default:
        return r.note || "—";
    }
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <h2 className="font-semibold">{t("sources_title")}</h2>
      <p className="mb-3 mt-1 text-xs text-slate-500 dark:text-slate-400">
        {t("sources_desc")}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-slate-500 dark:text-slate-400">
            <tr className="border-b border-slate-200 dark:border-slate-800">
              <th className="py-1.5 pr-3">{t("col_tool")}</th>
              <th className="pr-3">{t("col_indexes")}</th>
              <th className="pr-3">{t("col_status")}</th>
              <th className="pr-3">{t("col_findings")}</th>
              <th>{t("col_note")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.name}
                className="border-b border-slate-100 dark:border-slate-800/60"
              >
                <td className="py-1.5 pr-3 font-medium">{r.label}</td>
                <td className="pr-3 text-slate-500 dark:text-slate-400">
                  {r.desc}
                </td>
                <td className="pr-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      r.status === "used"
                        ? statusBadge.used
                        : skipBadge[r.skipKind ?? "other"]
                    }`}
                  >
                    {statusLabel(r)}
                  </span>
                </td>
                <td className="pr-3">{r.status === "used" ? r.count : "—"}</td>
                <td
                  className={
                    r.skipKind
                      ? `text-xs ${noteBadge[r.skipKind]}`
                      : "text-slate-500 dark:text-slate-400"
                  }
                >
                  {displayNote(r)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {routing && routing.not_applicable.length > 0 ? (
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer font-medium text-slate-600 dark:text-slate-400">
            {t("routing_not_applicable")} ({routing.not_applicable.length})
          </summary>
          <ul className="mt-2 max-h-36 space-y-1 overflow-y-auto text-xs text-slate-500">
            {routing.not_applicable.map((e) => (
              <li key={e.source}>
                <span className="font-medium">{e.label ?? e.source}</span> — {e.reason}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}
