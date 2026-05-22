import { useI18n } from "../i18n";

const styles: Record<string, string> = {
  verified: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  likely: "bg-sky-500/15 text-sky-700 dark:text-sky-300",
  historical: "bg-violet-500/15 text-violet-700 dark:text-violet-300",
  unverified: "bg-slate-500/15 text-slate-600 dark:text-slate-400",
  noisy: "bg-amber-500/15 text-amber-800 dark:text-amber-200",
  possible_false_positive: "bg-red-500/15 text-red-700 dark:text-red-300",
};

const LABEL_KEYS = new Set([
  "verified",
  "likely",
  "historical",
  "unverified",
  "noisy",
  "possible_false_positive",
]);

interface Props {
  label: string | null | undefined;
  reason?: string | null;
}

export function QualityBadge({ label, reason }: Props) {
  const { t } = useI18n();
  if (!label) return null;
  const i18nKey = LABEL_KEYS.has(label) ? `quality_${label}` : "quality_unverified";
  const cls = styles[label] ?? styles.unverified;
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs ${cls}`}
      title={reason ?? undefined}
    >
      {t(i18nKey)}
    </span>
  );
}
