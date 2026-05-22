import { NavLink, Outlet } from "react-router-dom";
import { ApiKeyPanel } from "../components/ApiKeyPanel";
import { Header } from "../components/Header";
import { useApiAuth } from "../context/ApiAuthContext";
import { useTheme } from "../hooks/useTheme";
import { useI18n } from "../i18n";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `block rounded-lg px-3 py-2 text-sm ${
    isActive
      ? "bg-sky-600/15 font-medium text-sky-700 dark:text-sky-300"
      : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
  }`;

export function AppShell() {
  const { t } = useI18n();
  const [theme, toggleTheme] = useTheme();
  const { apiKey, requiresApiKey, configLoaded } = useApiAuth();

  return (
    <div className="min-h-full bg-slate-100 text-slate-800 dark:bg-slate-950 dark:text-slate-200">
      <Header theme={theme} onToggleTheme={toggleTheme} />
      <div className="mx-auto flex w-full max-w-screen-2xl gap-6 px-4 py-6 lg:px-6">
        <aside className="w-52 shrink-0">
          <nav className="space-y-1 rounded-xl border border-slate-200 bg-white p-2 dark:border-slate-800 dark:bg-slate-900">
            <NavLink to="/dashboard" className={navClass}>
              {t("nav_dashboard")}
            </NavLink>
            <NavLink to="/cases" className={navClass}>
              {t("nav_cases")}
            </NavLink>
            <NavLink to="/scan" className={navClass}>
              {t("nav_quick_scan")}
            </NavLink>
          </nav>
        </aside>
        <main className="min-w-0 flex-1 space-y-4">
          {configLoaded && requiresApiKey && !apiKey ? (
            <ApiKeyPanel compact />
          ) : null}
          <Outlet />
        </main>
      </div>
      <footer className="mx-auto w-full max-w-screen-2xl px-4 py-6 text-xs text-slate-400 lg:px-6 dark:text-slate-600">
        {t("footer")}
      </footer>
    </div>
  );
}
