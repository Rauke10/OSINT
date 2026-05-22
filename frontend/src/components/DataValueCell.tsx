import type { ReactNode } from "react";
import { useI18n } from "../i18n";

type Props = {
  value: string;
  badges?: ReactNode;
  className?: string;
};

export function DataValueCell({ value, badges, className = "" }: Props) {
  const { t } = useI18n();
  return (
    <div className={`min-w-[22rem] max-w-[37.5rem] ${className}`}>
      <div className="flex items-start gap-2">
        <span
          className="min-w-0 flex-1 text-sm leading-snug [overflow-wrap:anywhere] line-clamp-2"
          title={value}
        >
          {value}
        </span>
        <button
          type="button"
          onClick={() => navigator.clipboard.writeText(value)}
          className="shrink-0 rounded border border-slate-200 px-1.5 py-0.5 text-[10px] text-slate-500 hover:border-sky-400 hover:text-sky-600 dark:border-slate-700"
          title={t("data_copy")}
        >
          {t("data_copy")}
        </button>
      </div>
      {badges ? <div className="mt-0.5">{badges}</div> : null}
    </div>
  );
}
