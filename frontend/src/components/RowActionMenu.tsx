import { useI18n } from "../i18n";

export type RowAction = {
  key: string;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
};

type Props = {
  primary: RowAction[];
  secondary?: RowAction[];
};

const btn =
  "whitespace-nowrap rounded border border-transparent px-1.5 py-0.5 text-xs hover:border-slate-200 dark:hover:border-slate-700 disabled:opacity-40";

export function RowActionMenu({ primary, secondary = [] }: Props) {
  const { t } = useI18n();
  return (
    <div className="flex min-w-[14rem] flex-nowrap items-center gap-1">
      {primary.map((a) => (
        <button
          key={a.key}
          type="button"
          disabled={a.disabled}
          onClick={a.onClick}
          className={`${btn} ${a.className ?? "text-sky-600 dark:text-sky-400"}`}
        >
          {a.label}
        </button>
      ))}
      {secondary.length > 0 ? (
        <details className="relative inline-block">
          <summary
            className={`${btn} cursor-pointer list-none text-slate-500 marker:content-none [&::-webkit-details-marker]:hidden`}
          >
            {t("actions_more")} ▾
          </summary>
          <div className="absolute right-0 z-20 mt-1 min-w-[10rem] rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
            {secondary.map((a) => (
              <button
                key={a.key}
                type="button"
                disabled={a.disabled}
                onClick={(e) => {
                  e.preventDefault();
                  a.onClick();
                  (e.currentTarget.closest("details") as HTMLDetailsElement | null)?.removeAttribute(
                    "open",
                  );
                }}
                className={`block w-full px-3 py-1.5 text-left text-xs hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 ${a.className ?? "text-slate-700 dark:text-slate-300"}`}
              >
                {a.label}
              </button>
            ))}
          </div>
        </details>
      ) : null}
    </div>
  );
}
