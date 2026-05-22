"""Operational asset status for Data Explorer (Fase 2C.3)."""

from __future__ import annotations

from typing import Any

from globeye.services.finding_quality import TRUSTED_SOURCES, QualityLabel

LIVE_ACTIVE = frozenset({"live_200", "redirect"})
TECHNICAL_TYPES = frozenset({"domain", "subdomain", "ip", "url", "service", "certificate"})


def compute_operational_status(item: dict[str, Any]) -> str:
    """Derive a single operational label for explorer filtering."""
    if item.get("hidden") or item.get("review_status") == "discarded":
        return "discarded"
    if item.get("is_potential_false_positive") or item.get("quality_label") == (
        QualityLabel.POSSIBLE_FALSE_POSITIVE.value
    ):
        return "needs_review"
    etype = item.get("type") or ""
    live = item.get("live_status")
    ql = item.get("quality_label") or ""
    sources = set(item.get("sources") or [])

    if etype == "url" and item.get("is_wayback_url"):
        if live in LIVE_ACTIVE:
            return "active"
        if live == "not_found":
            return "inactive"
        if live in {"timeout", "network_error"}:
            return "unknown"
        if ql in {QualityLabel.HISTORICAL.value, QualityLabel.NOISY.value}:
            return "historical"
        return "needs_review"

    if etype in TECHNICAL_TYPES:
        if ql in {QualityLabel.VERIFIED.value, QualityLabel.LIKELY.value}:
            return "active"
        if live in LIVE_ACTIVE:
            return "active"
        if sources & TRUSTED_SOURCES:
            return "active"
        if ql in {QualityLabel.HISTORICAL.value, QualityLabel.NOISY.value}:
            return "historical"

    if etype == "email":
        if ql in {QualityLabel.VERIFIED.value, QualityLabel.LIKELY.value}:
            return "active"
        return "needs_review"

    if ql in {QualityLabel.HISTORICAL.value}:
        return "historical"
    if ql == QualityLabel.UNVERIFIED.value and not item.get("evidence_count"):
        return "needs_review"
    return "needs_review"


def operational_summary(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for it in items:
        st = str(it.get("operational_status") or compute_operational_status(it))
        counts[st] = counts.get(st, 0) + 1
        if it.get("live_status") == "not_checked" and it.get("is_wayback_url"):
            counts["pending_live_check"] = counts.get("pending_live_check", 0) + 1
        if it.get("evidence_count", 0) > 0:
            counts["with_evidence"] = counts.get("with_evidence", 0) + 1
    counts["total_assets"] = len(items)
    return counts
