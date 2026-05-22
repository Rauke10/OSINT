import { useI18n } from "../i18n";

type Props = {
  label?: string;
};

export function LoadingBlock({ label }: Props) {
  const { t } = useI18n();
  return (
    <p className="animate-pulse text-sm text-slate-500 dark:text-slate-400">
      {label ?? t("loading_generic")}
    </p>
  );
}
