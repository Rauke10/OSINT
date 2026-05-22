import { Link } from "react-router-dom";
import { useI18n } from "../i18n";

type Props = {
  caseId: number;
};

export function PostScanBanner({ caseId }: Props) {
  const { t } = useI18n();
  const base = `/cases/${caseId}`;

  return (
    <div className="rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 dark:border-emerald-800 dark:bg-emerald-950/30">
      <p className="font-medium text-emerald-900 dark:text-emerald-200">{t("post_scan_title")}</p>
      <p className="mt-1 text-sm text-emerald-800/90 dark:text-emerald-300/90">{t("post_scan_body")}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Link
          to={`${base}/entities`}
          className="rounded-lg bg-emerald-700 px-3 py-1.5 text-sm text-white hover:bg-emerald-600"
        >
          {t("post_scan_entities")}
        </Link>
        <Link
          to={`${base}/graph`}
          className="rounded-lg border border-emerald-600 px-3 py-1.5 text-sm text-emerald-800 hover:bg-emerald-100 dark:text-emerald-200 dark:hover:bg-emerald-900/40"
        >
          {t("post_scan_graph")}
        </Link>
      </div>
    </div>
  );
}
