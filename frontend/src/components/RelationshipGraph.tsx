import { useEffect, useMemo, useRef, useState } from "react";
import cytoscape from "cytoscape";
import { useI18n } from "../i18n";
import type { Confidence, Finding, ScanResult } from "../types";

const COLORS: Record<string, string> = {
  domain: "#38bdf8",
  subdomain: "#38bdf8",
  email: "#fbbf24",
  username: "#34d399",
  profile: "#34d399",
  url: "#a78bfa",
  repo: "#a78bfa",
  paste: "#a78bfa",
  service: "#f87171",
  breach: "#f87171",
};

/** Above this many findings the graph is capped to the highest-signal nodes. */
const CAP = 500;
/** How many findings to keep when the graph is capped. */
const TOP_N = 300;

const confScore: Record<Confidence, number> = { low: 1, medium: 2, high: 3 };
const repScore: Record<string, number> = { sensitive: 3, notable: 2, info: 1 };

/** Rank a finding by confidence + reputation — higher means more signal. */
function signal(f: Finding): number {
  const rep = String(f.normalized_data.reputation ?? "info");
  return confScore[f.confidence] + (repScore[rep] ?? 0);
}

export function RelationshipGraph({ result }: { result: ScanResult }) {
  const { t } = useI18n();
  const ref = useRef<HTMLDivElement>(null);
  const [showAll, setShowAll] = useState(false);
  const [entityCount, setEntityCount] = useState(0);

  const total = result.findings.length;
  const capped = total > CAP && !showAll;

  const shown = useMemo(() => {
    if (result.findings.length <= CAP || showAll) return result.findings;
    return [...result.findings].sort((a, b) => signal(b) - signal(a)).slice(0, TOP_N);
  }, [result.findings, showAll]);

  useEffect(() => {
    const container = ref.current;
    if (!container) return;

    const root = result.target.value;
    const nodes = new Map<string, cytoscape.ElementDefinition>();
    nodes.set(root, { data: { id: root, label: root, col: "#e2e8f0", root: 1 } });
    const edges: cytoscape.ElementDefinition[] = [];
    const seen = new Set<string>();

    for (const f of shown) {
      const hint = f.graph_node_hint;
      const id = hint?.node_id ?? f.value;
      const type = hint?.node_type ?? f.kind;
      const parent = hint?.parent_id ?? root;
      const label = (hint?.label ?? f.value).slice(0, 38);
      if (!nodes.has(id)) {
        nodes.set(id, { data: { id, label, col: COLORS[type] ?? "#94a3b8" } });
      }
      if (!nodes.has(parent)) {
        nodes.set(parent, {
          data: { id: parent, label: parent.slice(0, 38), col: "#94a3b8" },
        });
      }
      const edgeId = `${parent}|${id}|${f.source}`;
      if (parent !== id && !seen.has(edgeId)) {
        seen.add(edgeId);
        edges.push({ data: { id: edgeId, source: parent, target: id } });
      }
    }

    setEntityCount(nodes.size - 1);

    const cy = cytoscape({
      container,
      elements: [...nodes.values(), ...edges],
      minZoom: 0.2,
      maxZoom: 3,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(col)",
            label: "data(label)",
            "font-size": 7,
            color: "#94a3b8",
            "text-valign": "bottom",
            width: 11,
            height: 11,
          },
        },
        {
          selector: "node[root]",
          style: { width: 22, height: 22, "font-size": 11 },
        },
        {
          selector: "edge",
          style: { "line-color": "#64748b66", width: 1, "curve-style": "haystack" },
        },
      ],
      layout: { name: "cose", animate: false },
    });
    return () => cy.destroy();
  }, [result.target.value, shown]);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <h2 className="mb-3 font-semibold">{t("graph_title")}</h2>
      <div
        ref={ref}
        className="h-[420px] rounded-lg border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950"
      />
      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
        {capped ? (
          <>
            {t("graph_capped")}
            {" · "}
            <button
              type="button"
              onClick={() => setShowAll(true)}
              className="text-sky-500 underline hover:no-underline"
            >
              {t("graph_show_all")} ({total})
            </button>
          </>
        ) : (
          `${entityCount} ${t("graph_entities")}`
        )}
      </p>
    </section>
  );
}
