import { useI18n } from "../i18n";
import type { ScanResult, SourceInfo } from "../types";

interface Props {
  result: ScanResult;
  catalog: SourceInfo[];
}

interface Row {
  name: string;
  label: string;
  desc: string;
  status: "used" | "skipped";
  count: number;
  note: string;
}

export function SourcesPanel({ result, catalog }: Props) {
  const { t } = useI18n();
  const meta = new Map(catalog.map((c) => [c.name, c]));

  const counts: Record<string, number> = {};
  for (const f of result.findings) {
    counts[f.source] = (counts[f.source] ?? 0) + 1;
  }

  const rows: Row[] = [];
  for (const name of result.summary.sources_used) {
    const m = meta.get(name);
    rows.push({
      name,
      label: m?.label ?? name,
      desc: m?.description ?? "",
      status: "used",
      count: counts[name] ?? 0,
      note: "",
    });
  }
  for (const [name, note] of Object.entries(result.summary.sources_skipped)) {
    const m = meta.get(name);
    rows.push({
      name,
      label: m?.label ?? name,
      desc: m?.description ?? "",
      status: "skipped",
      count: 0,
      note,
    });
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
                    className={
                      "rounded-full px-2 py-0.5 text-xs " +
                      (r.status === "used"
                        ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                        : "bg-slate-500/15 text-slate-500")
                    }
                  >
                    {r.status === "used" ? t("status_used") : t("status_skipped")}
                  </span>
                </td>
                <td className="pr-3">{r.status === "used" ? r.count : "—"}</td>
                <td className="text-slate-500 dark:text-slate-400">
                  {r.note || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
