import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, createCase } from "../../api";
import { ApiKeyPanel } from "../../components/ApiKeyPanel";
import { useApiAuth } from "../../context/ApiAuthContext";
import { useI18n } from "../../i18n";

export function CaseNewPage() {
  const { t } = useI18n();
  const { apiKey, requiresApiKey } = useApiAuth();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!title.trim()) {
      setError(t("case_title_required"));
      return;
    }
    if (requiresApiKey && !apiKey) {
      setError(t("api_key_required_title"));
      return;
    }
    setLoading(true);
    try {
      const c = await createCase(
        { title: title.trim(), description: description.trim() || undefined },
        apiKey,
      );
      navigate(`/cases/${c.id}/search`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-lg space-y-4">
      <Link to="/cases" className="text-xs text-sky-600 hover:underline dark:text-sky-400">
        ← {t("nav_cases")}
      </Link>
      <h1 className="text-xl font-bold">{t("case_new")}</h1>
      <p className="text-sm text-slate-500 dark:text-slate-400">{t("case_new_intro")}</p>

      {requiresApiKey && !apiKey ? <ApiKeyPanel /> : null}

      <form
        onSubmit={onSubmit}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
      >
        <label className="block text-sm">
          <span className="text-slate-500">{t("case_title")}</span>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-500">{t("case_description")}</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
          />
        </label>
        {error ? <p className="text-sm text-red-600 dark:text-red-400">{error}</p> : null}
        <button
          type="submit"
          disabled={loading || (requiresApiKey && !apiKey)}
          className="rounded-lg bg-sky-600 px-4 py-2 text-sm text-white hover:bg-sky-500 disabled:opacity-50"
        >
          {loading ? t("form_scanning") : t("case_create_and_scan")}
        </button>
      </form>
    </div>
  );
}
