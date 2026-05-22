import { useI18n } from "../../i18n";

export function CaseReportsPage() {
  const { t } = useI18n();
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center dark:border-slate-700 dark:bg-slate-900/50">
      <h2 className="text-lg font-semibold">{t("reports_title")}</h2>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{t("reports_placeholder")}</p>
    </div>
  );
}
