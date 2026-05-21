import { useMemo, useState } from "react";
import { useI18n } from "../i18n";
import type { Confidence, Finding } from "../types";

const PAGE = 50;

const confClass: Record<Confidence, string> = {
  high: "text-red-500",
  medium: "text-amber-500",
  low: "text-emerald-500",
};

const confRank: Record<Confidence, number> = { low: 1, medium: 2, high: 3 };

interface Group {
  value: string;
  kind: string;
  sources: string[];
  confidence: Confidence;
}

/** Collapse findings with the same value, keeping every source that saw it. */
function groupByValue(findings: Finding[]): Group[] {
  const map = new Map<string, Group>();
  for (const f of findings) {
    const g = map.get(f.value);
    if (!g) {
      map.set(f.value, {
        value: f.value,
        kind: f.kind,
        sources: [f.source],
        confidence: f.confidence,
      });
    } else {
      if (!g.sources.includes(f.source)) g.sources.push(f.source);
      if (confRank[f.confidence] > confRank[g.confidence]) {
        g.confidence = f.confidence;
      }
    }
  }
  return [...map.values()];
}

export function FindingsTable({ findings }: { findings: Finding[] }) {
  const { t } = useI18n();
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(1);
  const [grouped, setGrouped] = useState(false);

  const matched = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return findings;
    return findings.filter((f) =>
      `${f.source} ${f.kind} ${f.value} ${f.confidence}`.toLowerCase().includes(q),
    );
  }, [findings, filter]);

  const groups = useMemo(
    () => (grouped ? groupByValue(matched) : []),
    [grouped, matched],
  );

  const total = grouped ? groups.length : matched.length;
  const pages = Math.max(1, Math.ceil(total / PAGE));
  const current = Math.min(page, pages);
  const start = (current - 1) * PAGE;
  const findingRows = grouped ? [] : matched.slice(start, start + PAGE);
  const groupRows = grouped ? groups.slice(start, start + PAGE) : [];

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-semibold">{t("findings_title")}</h2>
        <div className="flex items-center gap-3">
          <label className="flex select-none items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <input
              type="checkbox"
              checked={grouped}
              onChange={(e) => {
                setGrouped(e.target.checked);
                setPage(1);
              }}
            />
            {t("group_by_value")}
          </label>
          <input
            type="search"
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value);
              setPage(1);
            }}
            placeholder={t("filter_ph")}
            className="w-56 max-w-[55vw] rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800"
          />
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-slate-500 dark:text-slate-400">
            <tr className="border-b border-slate-200 dark:border-slate-800">
              {grouped ? (
                <>
                  <th className="py-1.5 pr-3">{t("col_value")}</th>
                  <th className="pr-3">{t("col_kind")}</th>
                  <th className="pr-3">{t("col_sources")}</th>
                  <th>{t("col_conf")}</th>
                </>
              ) : (
                <>
                  <th className="py-1.5 pr-3">{t("col_source")}</th>
                  <th className="pr-3">{t("col_kind")}</th>
                  <th className="pr-3">{t("col_value")}</th>
                  <th>{t("col_conf")}</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {grouped
              ? groupRows.map((g) => (
                  <tr
                    key={g.value}
                    className="border-b border-slate-100 dark:border-slate-800/60"
                  >
                    <td className="break-all py-1.5 pr-3">{g.value}</td>
                    <td className="pr-3">
                      <code>{g.kind}</code>
                    </td>
                    <td className="pr-3">{g.sources.join(", ")}</td>
                    <td className={confClass[g.confidence]}>{g.confidence}</td>
                  </tr>
                ))
              : findingRows.map((f, i) => (
                  <tr
                    key={`${f.source}-${f.kind}-${f.value}-${i}`}
                    className="border-b border-slate-100 dark:border-slate-800/60"
                  >
                    <td className="py-1.5 pr-3">{f.source}</td>
                    <td className="pr-3">
                      <code>{f.kind}</code>
                    </td>
                    <td className="break-all pr-3">{f.value}</td>
                    <td className={confClass[f.confidence]}>{f.confidence}</td>
                  </tr>
                ))}
            {total === 0 && (
              <tr>
                <td colSpan={4} className="py-3 text-slate-500">
                  {t("no_findings")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
        <button
          type="button"
          onClick={() => setPage(current - 1)}
          disabled={current <= 1}
          className="rounded-lg border border-slate-300 px-3 py-1 disabled:opacity-40 dark:border-slate-700"
        >
          {t("prev")}
        </button>
        <span>
          {total} {grouped ? t("col_value") : t("col_findings")} · {t("page")} {current}
          /{pages}
        </span>
        <button
          type="button"
          onClick={() => setPage(current + 1)}
          disabled={current >= pages}
          className="rounded-lg border border-slate-300 px-3 py-1 disabled:opacity-40 dark:border-slate-700"
        >
          {t("next")}
        </button>
      </div>
    </section>
  );
}
