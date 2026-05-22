import { useI18n } from "../i18n";

const CATEGORY_CARDS: { key: string; labelKey: string }[] = [
  { key: "admin_login", labelKey: "wb_cat_admin" },
  { key: "api_endpoint", labelKey: "wb_cat_api" },
  { key: "backup_archive", labelKey: "wb_cat_backup" },
  { key: "document", labelKey: "wb_cat_document" },
  { key: "upload", labelKey: "wb_cat_upload" },
  { key: "wordpress", labelKey: "wb_cat_wordpress" },
  { key: "static_asset", labelKey: "wb_cat_static" },
  { key: "other", labelKey: "wb_cat_other" },
];

export function WaybackGroupingPanel({
  groups,
  activeCategory,
  onSelectCategory,
  onViewUrls,
  onCheckHighPriority,
  checking,
}: {
  groups: Record<
    string,
    {
      total: number;
      visible?: number;
      live: number;
      unchecked: number;
      not_found: number;
      discarded?: number;
    }
  >;
  activeCategory: string | null;
  onSelectCategory: (cat: string | null) => void;
  onViewUrls: (cat: string) => void;
  onCheckHighPriority: () => void;
  checking: boolean;
}) {
  const { t } = useI18n();
  const hasAny = Object.values(groups).some((g) => g.total > 0);
  if (!hasAny) return null;

  return (
    <div className="rounded-xl border border-violet-200 bg-violet-50/50 p-4 dark:border-violet-900 dark:bg-violet-950/30">
      <h3 className="text-sm font-semibold">{t("wb_group_title")}</h3>
      <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{t("wb_group_help")}</p>
      <p className="mt-1 text-xs text-violet-700 dark:text-violet-300">{t("wb_group_nd")}</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {CATEGORY_CARDS.map((card) => {
          const g = groups[card.key];
          if (!g?.total) return null;
          const active = activeCategory === card.key;
          return (
            <button
              key={card.key}
              type="button"
              onClick={() => onSelectCategory(active ? null : card.key)}
              className={`rounded-lg border p-2 text-left text-xs ${
                active
                  ? "border-violet-500 bg-violet-500/10"
                  : "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900"
              }`}
            >
              <p className="font-medium">{t(card.labelKey)}</p>
              <p className="text-slate-500">
                {g.total} {t("data_card_total")} · {t("wb_visible")}: {g.visible ?? g.total} ·{" "}
                {t("wb_live")}: {g.live} · {t("wb_unchecked")}: {g.unchecked}
                {(g.discarded ?? 0) > 0 ? ` · ${t("ops_discarded")}: ${g.discarded}` : ""}
              </p>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onViewUrls(card.key);
                }}
                className="mt-1 text-sky-600 hover:underline dark:text-sky-400"
              >
                {t("wb_view_urls")}
              </button>
            </button>
          );
        })}
      </div>
      <button
        type="button"
        disabled={checking}
        onClick={onCheckHighPriority}
        className="mt-3 rounded-lg bg-violet-700 px-3 py-1.5 text-sm text-white hover:bg-violet-600 disabled:opacity-50"
      >
        {checking ? t("live_check_running") : t("wb_check_high")}
      </button>
    </div>
  );
}
