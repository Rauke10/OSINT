"""ASN helpers (offline, built on the GeoLite2-ASN database)."""

from __future__ import annotations

from typing import Any

from globeye.enrichment.geoip import GeoIPEnricher


def asn_for_ip(enricher: GeoIPEnricher, ip: str) -> dict[str, Any] | None:
    """Return ``{"asn": int, "org": str}`` for ``ip`` if a DB is configured."""
    return enricher.asn(ip)


def asn_from_rdap(normalized_data: dict[str, Any]) -> int | None:
    """Best-effort ASN extraction from an RDAP autnum finding payload."""
    handle = normalized_data.get("handle") or normalized_data.get("name")
    if isinstance(handle, str) and handle.upper().startswith("AS"):
        digits = handle[2:].strip()
        if digits.isdigit():
            return int(digits)
    return None
