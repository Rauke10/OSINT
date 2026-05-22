#!/usr/bin/env python3
"""Diagnose API source credentials and probe responses (masked).

Usage:
  uv run python scripts/diagnose_sources.py --probe
"""

from __future__ import annotations

import argparse
import asyncio

from globeye.config import Settings
from globeye.services.source_credentials import SOURCE_ENV_FIELDS
from globeye.services.source_diagnostics import enrich_status_row
from globeye.services.source_status import describe_source_status
from globeye.utils.redact import mask_secret


def _masked_configured(settings: Settings, name: str, fields: list[str]) -> str:
    for field in fields:
        val = getattr(settings, field, None)
        if val is None:
            return "empty"
        raw = val.get_secret_value() if hasattr(val, "get_secret_value") else str(val)
        if not str(raw).strip():
            return "empty"
        return mask_secret(str(raw))
    return "n/a"


async def _main(probe: bool) -> int:
    settings = Settings()
    rows = await describe_source_status(settings, probe=probe)
    enriched = [enrich_status_row(r, settings) for r in rows]

    print("GLOBEYE API diagnostics (secrets masked)")
    header = (
        f"{'source':<16} {'credential':<22} {'scan':<16} {'http':<5} "
        f"{'endpoint':<28} {'auth':<22} hint"
    )
    print(header)
    print("-" * len(header) * 2)
    for row in enriched:
        name = str(row["name"])
        fields = SOURCE_ENV_FIELDS.get(name, [])
        if row["requires_api_key"]:
            hint = _masked_configured(settings, name, fields)
            configured = "yes" if row["configured"] else f"no ({hint})"
        else:
            configured = "keyless"
        cred = row.get("credential_status") or row.get("status")
        scan = row.get("probe_scan_status") or "—"
        http = row.get("http_status") or "—"
        endpoint = (row.get("checked_endpoint_name") or "—")[:28]
        auth = (row.get("auth_method") or "—")[:22]
        err = row.get("provider_error_message_sanitized") or row.get("message") or ""
        fix = row.get("how_to_fix") or ""
        print(
            f"{name:<16} {cred!s:<22} {scan!s:<16} {http!s:<5} "
            f"{endpoint:<28} {auth:<22} {configured}"
        )
        if err:
            print(f"  error: {err}")
        if fix and fix != err:
            print(f"  how_to_fix: {fix}")
        if row.get("env_vars"):
            print(f"  env: {', '.join(row['env_vars'])}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true", help="HTTP probe (uses quota)")
    raise SystemExit(asyncio.run(_main(parser.parse_args().probe)))
