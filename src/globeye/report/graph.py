"""Build a relationship graph (cytoscape-compatible) from a scan result.

Nodes are discovered entities; edges record *which source* established the
relationship. The scan target is always the root node.
"""

from __future__ import annotations

from typing import Any

from globeye.core.models import ScanResult


def build_graph(result: ScanResult) -> dict[str, list[dict[str, Any]]]:
    """Return ``{"nodes": [...], "edges": [...]}`` for cytoscape / vis."""
    root_id = result.target.value
    nodes: dict[str, dict[str, Any]] = {
        root_id: {
            "data": {
                "id": root_id,
                "label": root_id,
                "type": result.target.type.value,
                "root": True,
            }
        }
    }
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()

    for f in result.findings:
        hint = f.graph_node_hint
        node_id = hint.node_id if hint else f.value
        node_type = hint.node_type if hint else f.kind
        label = hint.label if hint else f.value
        parent = hint.parent_id if hint and hint.parent_id else result.target.value

        nodes.setdefault(
            node_id,
            {
                "data": {
                    "id": node_id,
                    "label": label,
                    "type": node_type,
                    "reputation": f.normalized_data.get("reputation", "info"),
                }
            },
        )
        if parent not in nodes:
            nodes[parent] = {"data": {"id": parent, "label": parent, "type": "domain"}}
        ekey = (parent, node_id, f.source)
        if parent != node_id and ekey not in seen_edges:
            seen_edges.add(ekey)
            edges.append(
                {
                    "data": {
                        "id": f"{parent}->{node_id}:{f.source}",
                        "source": parent,
                        "target": node_id,
                        "via": f.source,
                    }
                }
            )

    return {"nodes": list(nodes.values()), "edges": edges}
