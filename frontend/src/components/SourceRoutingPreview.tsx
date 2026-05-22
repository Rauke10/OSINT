import { useI18n } from "../i18n";
import type { SourceRoutingPreview } from "../types";

interface Props {
  preview: SourceRoutingPreview | null;
  loading: boolean;
  error: string;
}

export function SourceRoutingPreviewPanel({ preview, loading, error }: Props) {
  const { t } = useI18n();

  if (loading) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">{t("routing_preview_loading")}</p>
    );
  }
  if (error) {
    return <p className="text-sm text-red-600 dark:text-red-400">{error}</p>;
  }
  if (!preview) return null;

  return (
    <div className="space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/50">
      <p className="text-sm text-slate-600 dark:text-slate-300">{t("routing_only_useful")}</p>
      <div className="flex flex-wrap gap-2 text-sm">
        <span className="rounded-full bg-sky-500/15 px-2 py-0.5 text-sky-800 dark:text-sky-200">
          {t("routing_type")}: {preview.target_type}
        </span>
        <span className="rounded-full bg-slate-500/15 px-2 py-0.5 text-slate-700 dark:text-slate-300">
          {preview.normalized_value}
        </span>
        <span className="rounded-full bg-violet-500/15 px-2 py-0.5 text-violet-800 dark:text-violet-200">
          {preview.profile}
        </span>
      </div>
      {preview.warnings.length > 0 ? (
        <ul className="list-inside list-disc text-sm text-amber-700 dark:text-amber-300">
          {preview.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      ) : null}
      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-200">
          {t("routing_will_run")} ({preview.will_run.length})
        </h3>
        {preview.will_run.length === 0 ? (
          <p className="text-sm text-slate-500">{t("routing_none_will_run")}</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {preview.will_run.map((e) => (
              <li key={e.source} className="flex flex-wrap gap-2">
                <span className="font-medium">{e.label ?? e.source}</span>
                <span className="text-slate-500">{e.reason}</span>
                {e.requires_key ? (
                  <span className="text-xs text-slate-400">
                    {e.configured ? t("routing_key_ok") : t("routing_key_missing")}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
      {preview.skipped_missing_key.length > 0 ? (
        <section>
          <h3 className="mb-2 text-sm font-semibold text-amber-800 dark:text-amber-200">
            {t("routing_skipped_key")} ({preview.skipped_missing_key.length})
          </h3>
          <ul className="space-y-1 text-sm text-amber-700 dark:text-amber-300">
            {preview.skipped_missing_key.map((e) => (
              <li key={e.source}>
                <span className="font-medium">{e.source}</span> — {e.reason}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {preview.not_applicable.length > 0 ? (
        <details className="text-sm">
          <summary className="cursor-pointer font-semibold text-slate-600 dark:text-slate-400">
            {t("routing_not_applicable")} ({preview.not_applicable.length})
          </summary>
          <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto text-slate-500">
            {preview.not_applicable.map((e) => (
              <li key={e.source}>
                <span className="font-medium">{e.source}</span> — {e.reason}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
