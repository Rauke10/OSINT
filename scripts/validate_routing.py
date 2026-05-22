#!/usr/bin/env python3
"""Preview source routing for real-world targets (no secrets printed).

Usage:
  uv run python scripts/validate_routing.py
  uv run python scripts/validate_routing.py --depth deep
"""

from __future__ import annotations

import argparse
import json

from globeye.config import Settings
from globeye.core.source_profiles import ScanDepth
from globeye.core.target import detect
from globeye.services.source_credentials import SOURCE_ENV_VARS, is_configured
from globeye.services.source_router import plan_routing
from globeye.sources.base import discover_sources

TARGETS = [
    ("8.8.8.8", "IP"),
    ("1.1.1.1", "IP"),
    ("example.com", "domain"),
    ("github.com", "domain"),
    ("wikipedia.org", "domain"),
    ("ecix.tech", "domain"),
    ("test@example.com", "email"),
    ("github", "username"),
    ("+34600111222", "phone"),
    ("Juan Pérez García", "person"),
]


def _configured_sources(settings: Settings) -> list[str]:
    out: list[str] = []
    for cls in discover_sources():
        if is_configured(settings, cls.name, requires_api_key=cls.requires_api_key):
            out.append(cls.name)
    return sorted(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--depth", default="standard", choices=[d.value for d in ScanDepth])
    args = parser.parse_args()
    depth = ScanDepth(args.depth)
    settings = Settings()

    print("# Routing validation preview")
    print(f"depth={depth.value}")
    print(f"configured_keyed_sources={_configured_sources(settings)}")
    print()

    for raw, label in TARGETS:
        target = detect(raw)
        plan = plan_routing(settings, target, depth=depth)
        block = {
            "label": label,
            "raw": raw,
            "target_type": plan.target_type,
            "normalized_value": plan.normalized_value,
            "profile": plan.profile,
            "will_run": [e.source for e in plan.will_run],
            "skipped_missing_key": [e.source for e in plan.skipped_missing_key],
            "not_applicable_count": len(plan.not_applicable),
            "not_applicable_sample": [e.source for e in plan.not_applicable[:5]],
            "warnings": plan.warnings,
        }
        print(f"## {raw} ({label})")
        print(json.dumps(block, indent=2, ensure_ascii=False))
        print()

    print("# Env vars reference (names only)")
    for name, vars_ in sorted(SOURCE_ENV_VARS.items()):
        print(f"  {name}: {', '.join(vars_)}")


if __name__ == "__main__":
    main()
