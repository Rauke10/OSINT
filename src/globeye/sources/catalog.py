"""Human-friendly catalogue of the passive sources GLOBEYE ships.

Single source of truth for tool labels/descriptions, shared by the HTML
report and the web UI (via ``GET /api/sources``).
"""

from __future__ import annotations

from typing import Any

from globeye.config import Settings
from globeye.core.context import ScanContext
from globeye.sources.base import discover_sources

# name -> (display label, what it indexes)
SOURCE_CATALOG: dict[str, tuple[str, str]] = {
    "crtsh": ("crt.sh", "Certificate Transparency logs (subdomains/certs)"),
    "rdap": ("RDAP / WHOIS", "Registration data for domains, IPs and ASNs"),
    "shodan": ("Shodan", "Services & DNS already indexed by Shodan"),
    "censys": ("Censys", "Host view + certificate name search"),
    "securitytrails": ("SecurityTrails", "Passive DNS / subdomains"),
    "otx": ("AlienVault OTX", "Passive DNS"),
    "wayback": ("Wayback Machine", "Archived URLs (Internet Archive CDX)"),
    "hibp": ("Have I Been Pwned", "Breach membership for an email"),
    "hunter": ("Hunter.io", "Email pattern / known emails for a domain"),
    "dehashed": ("DeHashed", "Breach metadata (no credential values stored)"),
    "gravatar": ("Gravatar", "Public profile bound to an email hash"),
    "github": ("GitHub code search", "Public code referencing the target"),
    "pastebin": ("Pastebin (Google CSE)", "Public pastes via the Google index"),
    "username_enum": ("Social profiles", "Public-profile presence per platform"),
    "urlscan": ("urlscan.io", "URLs already scanned by urlscan (search index)"),
    "chaos": ("Chaos (ProjectDiscovery)", "Precomputed subdomain dataset"),
    "greynoise": ("GreyNoise Community", "IP background-noise classification"),
    "emailrep": ("EmailRep", "Aggregated reputation of an email address"),
    "urlhaus": ("URLhaus (abuse.ch)", "Malicious URLs known for a host"),
    "threatfox": ("ThreatFox (abuse.ch)", "Indicators of compromise (IoCs)"),
}


def label_for(name: str) -> tuple[str, str]:
    """Return ``(label, description)`` for a source name."""
    return SOURCE_CATALOG.get(name, (name, ""))


def describe_sources(settings: Settings) -> list[dict[str, Any]]:
    """Catalogue every registered source with metadata and availability."""
    ctx = ScanContext.create(settings)
    rows: list[dict[str, Any]] = []
    for cls in discover_sources():
        label, desc = label_for(cls.name)
        rows.append(
            {
                "name": cls.name,
                "label": label,
                "description": desc,
                "requires_api_key": cls.requires_api_key,
                "available": cls(ctx).available(),
                "targets": sorted(t.value for t in cls.supported_target_types),
            }
        )
    return sorted(rows, key=lambda r: str(r["name"]))
