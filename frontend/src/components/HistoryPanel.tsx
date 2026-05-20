import { useI18n } from "../i18n";
import type { HistoryItem } from "../types";

interface Props {
  history: HistoryItem[];
  onOpen: (item: HistoryItem) => void;
  onRefresh: () => void;
}

export function HistoryPanel({ history, onOpen, onRefresh }: Props) {
  const { t } = useI18n();

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold">{t("history_title")}</h2>
        <button
          type="button"
          onClick={onRefresh}
          className="rounded-lg border border-slate-300 px-3 py-1 text-sm hover:border-sky-500 dark:border-slate-700"
        >
          {t("refresh")}
        </button>
      </div>
      {history.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {t("history_empty")}
        </p>
      ) : (
        <div className="divide-y divide-slate-100 dark:divide-slate-800/60">
          {history.map((h) => (
            <button
              key={h.id}
              type="button"
              onClick={() => onOpen(h)}
              className="flex w-full items-center gap-3 py-2 text-left hover:text-sky-500"
            >
              <span className="w-10 text-xs text-slate-400 dark:text-slate-500">
                #{h.id}
              </span>
              <span className="font-medium">{h.target_value}</span>
              <span className="text-xs text-slate-400 dark:text-slate-500">
                {h.target_type}
              </span>
              <span className="ml-auto text-xs text-slate-500 dark:text-slate-400">
                {h.total_findings} {t("col_findings")} ·{" "}
                {h.created_at.slice(0, 16).replace("T", " ")}
              </span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
