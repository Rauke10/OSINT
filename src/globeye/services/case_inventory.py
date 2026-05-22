"""Approved inventory view (Fase 2D)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Engine

from globeye.services.case_data import build_case_data


def build_case_inventory(
    engine: Engine,
    case_id: int,
    *,
    type_filter: str | None = None,
    source_filter: str | None = None,
    query: str | None = None,
    live_status_filter: str | None = None,
    wayback_category: str | None = None,
    wayback_priority: str | None = None,
    inventory_priority: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> dict[str, Any]:
    """Only manually approved, non-hidden entities."""
    return build_case_data(
        engine,
        case_id,
        type_filter=type_filter,
        source_filter=source_filter,
        query=query,
        live_status_filter=live_status_filter,
        wayback_category=wayback_category,
        wayback_priority=wayback_priority,
        hide_discarded=True,
        inventory_status_filter="approved",
        limit=limit,
        offset=offset,
    )
