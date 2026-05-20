"""Standalone interactive HTML report (Jinja2, self-contained).

The findings dataset is embedded **once** as JSON; the table (paginated),
the grouped timeline and the clustered relationship graph are all derived
from it in the browser. This keeps the file small and usable even for
scans with thousands of findings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from globeye import __version__
from globeye.core.models import ScanResult
from globeye.sources.catalog import label_for

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml", "j2"]),
)


def _sources_payload(result: ScanResult) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for name in sorted(result.sources_used):
        label, desc = label_for(name)
        rows.append({"name": name, "label": label, "desc": desc, "status": "used", "note": ""})
    for name in sorted(result.sources_skipped):
        label, desc = label_for(name)
        rows.append(
            {
                "name": name,
                "label": label,
                "desc": desc,
                "status": "skipped",
                "note": result.sources_skipped[name],
            }
        )
    return rows


def _findings_payload(result: ScanResult) -> list[dict[str, Any]]:
    return [
        {
            "source": f.source,
            "kind": f.kind,
            "value": f.value,
            "confidence": f.confidence.value,
            "timestamp": f.timestamp.isoformat(),
            "reputation": f.normalized_data.get("reputation", "info"),
            "node_type": (f.graph_node_hint.node_type if f.graph_node_hint else f.kind),
        }
        for f in result.findings
    ]


def to_html(result: ScanResult) -> str:
    """Render the scan result to a single self-contained HTML document."""
    findings = _findings_payload(result)
    template = _env.get_template("report.html.j2")
    return template.render(
        target=result.target.model_dump(mode="json"),
        generated_at=result.finished_at.isoformat(),
        duration=round(result.duration_seconds, 2),
        version=__version__,
        summary=result.summary(),
        sources_used=result.sources_used,
        sources_skipped=list(result.sources_skipped),
        pivoted=[t.value for t in result.pivoted_targets],
        findings_json=json.dumps(findings, separators=(",", ":")),
        sources_json=json.dumps(_sources_payload(result), separators=(",", ":")),
    )


def write_html(result: ScanResult, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_html(result), encoding="utf-8")
    return out
