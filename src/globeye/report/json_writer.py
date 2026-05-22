"""Machine-readable JSON report writer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from globeye.core.models import ScanResult


def to_dict(result: ScanResult) -> dict[str, Any]:
    """Serialize a scan result, with a small summary block on top."""
    out: dict[str, Any] = {
        "target": result.target.model_dump(mode="json"),
        "summary": {
            "duration_seconds": round(result.duration_seconds, 3),
            "sources_used": result.sources_used,
            "sources_skipped": result.sources_skipped,
            "findings": result.summary(),
            "pivoted_targets": [t.model_dump(mode="json") for t in result.pivoted_targets],
        },
        "findings": [f.model_dump(mode="json") for f in result.findings],
    }
    if result.routing is not None:
        out["routing"] = result.routing
    return out


def to_json(result: ScanResult, *, indent: int = 2) -> str:
    return json.dumps(to_dict(result), indent=indent, default=str)


def write_json(result: ScanResult, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_json(result), encoding="utf-8")
    return out
