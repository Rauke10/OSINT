import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import { useI18n } from "../i18n";
import type { GraphPayload, ScanResult } from "../types";

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

type Props =
  | { result: ScanResult; graph?: never; titleKey: string; subtitleKey: string }
  | { graph: GraphPayload; result?: never; titleKey: string; subtitleKey: string };

export function RelationshipGraph(props: Props) {
  const { t } = useI18n();
  const ref = useRef<HTMLDivElement>(null);
  const [note, setNote] = useState("");

  useEffect(() => {
    const container = ref.current;
    if (!container) return;

    let elements: cytoscape.ElementDefinition[];

    if ("graph" in props && props.graph) {
      elements = [
        ...props.graph.nodes.map((n) => {
          const d = n.data as Record<string, unknown>;
          const type = String(d.type ?? "unknown");
          return {
            data: {
              ...d,
              col: COLORS[type] ?? "#94a3b8",
              label: String(d.label ?? d.value ?? d.id).slice(0, 38),
            },
          };
        }),
        ...props.graph.edges.map((e) => ({ data: e.data })),
      ];
      setNote(
        `${props.graph.nodes.length} ${t("graph_entities")} · ${props.graph.edges.length} ${t("graph_edges")}`,
      );
    } else if (props.result) {
      const result = props.result;
      const root = result.target.value;
      const nodes = new Map<string, cytoscape.ElementDefinition>();
      nodes.set(root, { data: { id: root, label: root, col: "#e2e8f0", root: 1 } });
      const edges: cytoscape.ElementDefinition[] = [];
      const seen = new Set<string>();

      for (const f of result.findings.slice(0, 200)) {
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
      elements = [...nodes.values(), ...edges];
      setNote(
        result.findings.length > 200
          ? t("graph_truncated")
          : `${nodes.size - 1} ${t("graph_entities")}`,
      );
    } else {
      return;
    }

    const cy = cytoscape({
      container,
      elements,
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
  }, [props, t]);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <h2 className="font-semibold">{t(props.titleKey)}</h2>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">{t(props.subtitleKey)}</p>
      <div
        ref={ref}
        className="h-[420px] rounded-lg border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950"
      />
      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{note}</p>
    </section>
  );
}
