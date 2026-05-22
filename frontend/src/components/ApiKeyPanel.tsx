import { useState } from "react";
import { Link } from "react-router-dom";
import { useApiAuth } from "../context/ApiAuthContext";
import { useI18n } from "../i18n";

type Props = {
  /** Called after the user saves a non-empty key (optional). */
  onSaved?: () => void;
  compact?: boolean;
};

export function ApiKeyPanel({ onSaved, compact = false }: Props) {
  const { t } = useI18n();
  const { apiKey, setApiKey, apiDebug } = useApiAuth();
  const [draft, setDraft] = useState(apiKey);

  if (apiDebug) {
    return (
      <p className="text-xs text-slate-500 dark:text-slate-400">{t("api_debug_hint")}</p>
    );
  }

  const save = () => {
    const trimmed = draft.trim();
    setApiKey(trimmed);
    if (trimmed) onSaved?.();
  };

  return (
    <div
      className={
        compact
          ? "space-y-2"
          : "space-y-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-800 dark:bg-amber-950/40"
      }
    >
      <p className={compact ? "text-sm text-amber-900 dark:text-amber-200" : "font-medium text-amber-900 dark:text-amber-200"}>
        {t("api_key_required_title")}
      </p>
      <p className="text-xs text-amber-800/90 dark:text-amber-300/90">{t("api_key_required_body")}</p>
      <label className="block text-xs">
        <span className="font-medium text-slate-600 dark:text-slate-400">{t("form_key")}</span>
        <input
          type="password"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && save()}
          placeholder="X-API-Key"
          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
        />
      </label>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={save}
          className="rounded-lg bg-sky-600 px-3 py-1.5 text-sm text-white hover:bg-sky-500"
        >
          {t("api_key_save")}
        </button>
        <Link
          to="/scan"
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:border-sky-500 dark:border-slate-700"
        >
          {t("nav_quick_scan")}
        </Link>
      </div>
    </div>
  );
}
