import { useI18n } from "../i18n";

interface Props {
  target: string;
  setTarget: (v: string) => void;
  pivot: boolean;
  setPivot: (v: boolean) => void;
  loading: boolean;
  error: string;
  onScan: () => void;
  scanLabel?: string;
}

const inputCls =
  "mt-1 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 " +
  "focus:outline-none focus:ring-2 focus:ring-sky-500 " +
  "dark:border-slate-700 dark:bg-slate-800";

export function ScanForm({
  target,
  setTarget,
  pivot,
  setPivot,
  loading,
  error,
  onScan,
  scanLabel,
}: Props) {
  const { t } = useI18n();

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <div className="grid gap-3 md:grid-cols-[1fr_auto]">
        <div className="space-y-3">
          <label className="block">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
              {t("form_target")}
            </span>
            <input
              type="text"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !loading && onScan()}
              placeholder={t("form_target_ph")}
              className={inputCls}
            />
          </label>
          <p className="text-xs text-slate-400 dark:text-slate-500">{t("form_pivot_hint")}</p>
        </div>
        <div className="flex gap-3 md:flex-col md:justify-end">
          <label className="flex select-none items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={pivot}
              onChange={(e) => setPivot(e.target.checked)}
            />
            {t("form_pivot")}
          </label>
          <button
            type="button"
            onClick={onScan}
            disabled={loading}
            className="rounded-lg bg-sky-600 px-6 py-2 font-medium text-white hover:bg-sky-500 disabled:cursor-default disabled:opacity-50"
          >
            {loading ? t("form_scanning") : (scanLabel ?? t("form_scan"))}
          </button>
        </div>
      </div>
      {error ? (
        <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>
      ) : null}
    </section>
  );
}
