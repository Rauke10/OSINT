#!/usr/bin/env python3
"""Check passive source credentials and optional light probes.

Usage:
  uv run python scripts/check_sources.py
  uv run python scripts/check_sources.py --probe

Never prints full API keys.
"""

from __future__ import annotations

import argparse
import asyncio

from globeye.config import Settings
from globeye.services.source_status import describe_source_status


def _print_table(rows: list[dict[str, object]], *, probed: bool) -> None:
    title = "GLOBEYE source status" + (" (probed)" if probed else "")
    print(title)
    print(f"{'source':<18} {'configured':<12} {'status':<14} message")
    print("-" * 72)
    for row in rows:
        name = str(row["name"])
        if not row["requires_api_key"]:
            configured = "keyless"
        elif row["configured"]:
            configured = "configured"
        else:
            configured = "missing_key"
        status = str(row["status"])
        message = str(row["message"])
        print(f"{name:<18} {configured:<12} {status:<14} {message}")


async def _main(probe: bool) -> int:
    settings = Settings()
    rows = await describe_source_status(settings, probe=probe)
    _print_table(rows, probed=probe)
    bad = [r for r in rows if r["status"] in {"invalid_key", "config_error", "network_error"}]
    return 1 if bad and probe else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--probe",
        action="store_true",
        help="run a light HTTP probe per source (consumes a little API quota)",
    )
    raise SystemExit(asyncio.run(_main(parser.parse_args().probe)))
