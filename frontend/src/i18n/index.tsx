import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Lang = "es" | "en";

type Entry = { en: string; es: string };

const DICT: Record<string, Entry> = {
  subtitle: { en: "strictly passive OSINT", es: "OSINT estrictamente pasivo" },
  docs: { en: "API docs", es: "API docs" },
  legal: {
    en: "Authorized / educational use only — scan assets you own or have written permission for. Results are personal data; handle per GDPR & local law.",
    es: "Solo uso autorizado / educativo — escanea activos propios o con permiso escrito. Los resultados son datos personales; trátalos conforme al RGPD y la ley local.",
  },
  form_target: { en: "Target", es: "Objetivo" },
  form_target_ph: {
    en: "domain · IP · email · username · ASN …",
    es: "dominio · IP · email · usuario · ASN …",
  },
  form_key: { en: "API key", es: "Clave API" },
  form_key_hint: {
    en: "(your self-hosted GLOBEYE_API_KEY — you choose it)",
    es: "(tu GLOBEYE_API_KEY autoalojada — la eliges tú)",
  },
  form_remember_key: {
    en: "Remember key on this device (localStorage)",
    es: "Recordar la clave en este dispositivo (localStorage)",
  },
  form_pivot: { en: "pivot", es: "pivotar" },
  form_scan: { en: "Scan", es: "Escanear" },
  form_scanning: { en: "Scanning…", es: "Escaneando…" },
  err_empty: { en: "Enter a target.", es: "Introduce un objetivo." },
  err_401: { en: "Invalid or missing API key.", es: "Clave API inválida o ausente." },
  err_503: {
    en: "Server has no GLOBEYE_API_KEY configured (set it in .env or use GLOBEYE_API_DEBUG=true).",
    es: "El servidor no tiene GLOBEYE_API_KEY configurada (ponla en .env o usa GLOBEYE_API_DEBUG=true).",
  },
  err_network: { en: "Network error", es: "Error de red" },
  target_word: { en: "Target", es: "Objetivo" },
  pivoted: { en: "pivoted", es: "pivotado" },
  card_findings: { en: "findings", es: "hallazgos" },
  card_high: { en: "high", es: "alta" },
  card_medium: { en: "medium", es: "media" },
  card_low: { en: "low", es: "baja" },
  sources_title: { en: "Sources consulted", es: "Fuentes consultadas" },
  sources_desc: {
    en: "Which passive OSINT tools were queried — GLOBEYE never contacts the target, only these third-party indexes.",
    es: "Qué herramientas OSINT pasivas se consultaron — GLOBEYE nunca contacta el objetivo, solo estos índices de terceros.",
  },
  col_tool: { en: "tool", es: "herramienta" },
  col_indexes: { en: "indexes", es: "qué indexa" },
  col_status: { en: "status", es: "estado" },
  col_findings: { en: "findings", es: "hallazgos" },
  col_note: { en: "note", es: "nota" },
  status_used: { en: "used", es: "usada" },
  status_skipped: { en: "skipped", es: "omitida" },
  graph_title: { en: "Relationship graph", es: "Grafo de relaciones" },
  graph_entities: { en: "related entities", es: "entidades relacionadas" },
  graph_capped: {
    en: "large graph — showing the highest-signal nodes",
    es: "grafo grande — mostrando los nodos de mayor señal",
  },
  graph_show_all: { en: "Show all", es: "Mostrar todos" },
  findings_title: { en: "Findings", es: "Hallazgos" },
  filter_ph: { en: "Filter…", es: "Filtrar…" },
  group_by_value: { en: "Group by value", es: "Agrupar por valor" },
  col_source: { en: "source", es: "fuente" },
  col_kind: { en: "kind", es: "tipo" },
  col_value: { en: "value", es: "valor" },
  col_sources: { en: "sources", es: "fuentes" },
  col_conf: { en: "conf", es: "conf" },
  no_findings: { en: "No matching findings.", es: "Sin hallazgos coincidentes." },
  prev: { en: "‹ Prev", es: "‹ Ant." },
  next: { en: "Next ›", es: "Sig. ›" },
  page: { en: "page", es: "página" },
  history_title: { en: "Scan history", es: "Historial de escaneos" },
  refresh: { en: "Refresh", es: "Actualizar" },
  history_empty: {
    en: "No saved scans yet (set your API key above and refresh).",
    es: "Aún no hay escaneos guardados (pon tu clave API arriba y actualiza).",
  },
  export_json: { en: "JSON", es: "JSON" },
  export_report: { en: "HTML report (PDF)", es: "Informe HTML (PDF)" },
  footer: {
    en: "GLOBEYE — strictly passive OSINT. The author is not responsible for misuse.",
    es: "GLOBEYE — OSINT estrictamente pasivo. El autor no se responsabiliza del mal uso.",
  },
  empty_hint: {
    en: "Enter a target above and run a scan to see results here.",
    es: "Introduce un objetivo arriba y ejecuta un escaneo para ver resultados.",
  },
};

interface I18nValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

function detectLang(): Lang {
  try {
    const saved = localStorage.getItem("globeye-lang");
    if (saved === "es" || saved === "en") return saved;
  } catch {
    /* ignore */
  }
  return navigator.language.toLowerCase().startsWith("es") ? "es" : "en";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(detectLang);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem("globeye-lang", l);
    } catch {
      /* ignore */
    }
  }, []);

  const t = useCallback((key: string) => DICT[key]?.[lang] ?? key, [lang]);

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
