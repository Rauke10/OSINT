import { useI18n } from "../i18n";
import type { UrlLiveStatus } from "../types";

const STATUS_KEYS: Record<string, string> = {
  not_checked: "live_status_not_checked",
  live_200: "live_status_live_200",
  redirect: "live_status_redirect",
  forbidden: "live_status_forbidden",
  not_found: "live_status_not_found",
  server_error: "live_status_server_error",
  timeout: "live_status_timeout",
  network_error: "live_status_network_error",
  invalid_url: "live_status_invalid_url",
};

const STATUS_CLASS: Record<string, string> = {
  not_checked: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
  live_200: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  redirect: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  forbidden: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  not_found: "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300",
  server_error: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  timeout: "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300",
  network_error: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  invalid_url: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
};

export function LiveStatusBadge({
  status,
  statusCode,
}: {
  status?: UrlLiveStatus | string | null;
  statusCode?: number | null;
}) {
  const { t } = useI18n();
  const key = status ?? "not_checked";
  const labelKey = STATUS_KEYS[key] ?? "live_status_not_checked";
  const cls = STATUS_CLASS[key] ?? STATUS_CLASS.not_checked;
  const code = statusCode != null ? ` (${statusCode})` : "";
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${cls}`}>
      {t(labelKey)}
      {code}
    </span>
  );
}
