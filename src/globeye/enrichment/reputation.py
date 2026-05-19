"""Offline, deterministic reputation tagging for findings.

No network, no third-party calls — a small heuristic that flags findings
worth a closer look (breaches, pastes, code leaks, sensitive hostnames).
"""

from __future__ import annotations

from globeye.core.models import Finding

SENSITIVE_KINDS = {"breach", "breach_record", "paste", "code_reference"}
_NOTABLE_HINTS = (
    "admin",
    "login",
    "vpn",
    "staging",
    "stage",
    "dev",
    "test",
    "internal",
    "intranet",
    "jenkins",
    "gitlab",
    "grafana",
    "kibana",
    "phpmyadmin",
    "backup",
    "old",
)


def assess(finding: Finding) -> str:
    """Return ``"sensitive"``, ``"notable"`` or ``"info"``."""
    if finding.kind in SENSITIVE_KINDS:
        return "sensitive"
    haystack = f"{finding.value}".lower()
    if any(hint in haystack for hint in _NOTABLE_HINTS):
        return "notable"
    return "info"
