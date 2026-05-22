import { useI18n, type Lang } from "../i18n";

interface Props {
  theme: "dark" | "light";
  onToggleTheme: () => void;
}

const segBtn = (active: boolean) =>
  `px-2.5 py-1 text-xs font-medium transition-colors ${
    active
      ? "bg-sky-600 text-white"
      : "text-slate-500 dark:text-slate-400 hover:text-sky-500"
  }`;

export function Header({ theme, onToggleTheme }: Props) {
  const { t, lang, setLang } = useI18n();
  const langs: Lang[] = ["es", "en"];

  return (
    <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="mx-auto flex w-full max-w-screen-2xl items-center justify-between gap-4 px-4 py-3 lg:px-6">
        <div className="flex items-center gap-2">
          <span className="text-xl" aria-hidden>
            🌐
          </span>
          <div>
            <h1 className="font-bold leading-tight">GLOBEYE</h1>
            <p className="text-xs leading-tight text-slate-500 dark:text-slate-400">
              {t("subtitle")}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <a
            href="/api/docs"
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-slate-300 px-3 py-1.5 hover:border-sky-500 dark:border-slate-700"
          >
            {t("docs")}
          </a>
          <div className="flex overflow-hidden rounded-lg border border-slate-300 dark:border-slate-700">
            {langs.map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => setLang(l)}
                className={segBtn(lang === l)}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={onToggleTheme}
            aria-label="Toggle theme"
            className="rounded-lg border border-slate-300 px-3 py-1.5 hover:border-sky-500 dark:border-slate-700"
          >
            {theme === "dark" ? "☀" : "☾"}
          </button>
        </div>
      </div>
    </header>
  );
}
