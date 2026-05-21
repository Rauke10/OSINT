import { useI18n } from "../i18n";

interface Props {
  target: string;
  setTarget: (v: string) => void;
  apiKey: string;
  setApiKey: (v: string) => void;
  remember: boolean;
  setRemember: (v: boolean) => void;
  pivot: boolean;
  setPivot: (v: boolean) => void;
  loading: boolean;
  error: string;
  onScan: () => void;
}

const inputCls =
  "mt-1 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 " +
  "focus:outline-none focus:ring-2 focus:ring-sky-500 " +
  "dark:border-slate-700 dark:bg-slate-800";

export function ScanForm({
  target,
  setTarget,
  apiKey,
  setApiKey,
  remember,
  setRemember,
  pivot,
  setPivot,
  loading,
  error,
  onScan,
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
              onKeyDown={(e) => e.key === "Enter" && onScan()}
              placeholder={t("form_target_ph")}
              className={inputCls}
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
              {t("form_key")}{" "}
              <span className="text-slate-400">{t("form_key_hint")}</span>
            </span>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="X-API-Key"
              className={inputCls}
            />
          </label>
          <label className="flex select-none items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
            />
            {t("form_remember_key")}
          </label>
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
            {loading ? t("form_scanning") : t("form_scan")}
          </button>
        </div>
      </div>
      {error && (
        <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </section>
  );
}
