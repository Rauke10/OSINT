import { useI18n } from "../i18n";

export function LegalBanner() {
  const { t } = useI18n();
  return (
    <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-2.5 text-xs text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300">
      ⚠️ {t("legal")}
    </div>
  );
}
