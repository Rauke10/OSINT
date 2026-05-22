"""Entity traceability for Data Explorer (Fase 2C.4)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

from globeye.core.models import Finding
from globeye.db.models import Entity, StoredEvidence
from globeye.services.entity_review import reviews_by_entity
from globeye.services.finding_quality import (
    _finding_matches_entity,
    load_case_findings,
)
from globeye.services.url_grouping import classify_wayback_url, wayback_group_reason
from globeye.services.url_live_check import latest_checks_by_entity
from globeye.services.url_normalization import normalize_url_for_entity, urls_are_equivalent

_URL_TYPES = frozenset({"url", "archived_url"})


def _related_findings(
    pairs: list[tuple[Finding, Any]],
    entity_type: str,
    normalized_value: str,
    display_value: str,
) -> list[Finding]:
    out: list[Finding] = []
    for finding, _ in pairs:
        if _finding_matches_entity(finding, entity_type, normalized_value):
            out.append(finding)
            continue
        if (
            entity_type in _URL_TYPES
            and finding.kind == "archived_url"
            and (
                urls_are_equivalent(finding.value, display_value)
                or urls_are_equivalent(finding.value, normalized_value)
            )
        ):
            out.append(finding)
    return out


def _original_values_for_entity(
    ent: Entity,
    related: list[Finding],
    evidence_rows: list[StoredEvidence],
) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add(val: str | None) -> None:
        if not val or val in seen:
            return
        seen.add(val)
        ordered.append(val)

    add(ent.display_value)
    add(ent.normalized_value)
    for f in related:
        add(f.value)
        if f.graph_node_hint is not None:
            add(f.graph_node_hint.label)
            add(f.graph_node_hint.node_id)
    for ev in evidence_rows:
        add(ev.finding_value)
        add(ev.source_url)
    return ordered


def build_entity_trace(engine: Engine, entity_id: int) -> dict[str, Any]:
    """Full trace payload for one explorer row (entity)."""
    with Session(engine) as session:
        ent = session.get(Entity, entity_id)
        if ent is None:
            return {"error": "entity not found"}

        case_id = int(ent.case_id)
        eid = int(ent.id or 0)
        evidence_rows = list(
            session.exec(
                select(StoredEvidence)
                .where(StoredEvidence.case_id == case_id)
                .where(StoredEvidence.entity_id == eid)
                .order_by(col(StoredEvidence.id))
            ).all()
        )
        evidence_ids = [int(ev.id) for ev in evidence_rows if ev.id is not None]

    pairs = load_case_findings(engine, case_id)
    related = _related_findings(pairs, ent.entity_type, ent.normalized_value, ent.display_value)
    original_values = _original_values_for_entity(ent, related, evidence_rows)
    sources = sorted({f.source for f in related})
    if not sources and evidence_rows:
        sources = sorted({ev.source_name for ev in evidence_rows})

    norm = None
    canonical_key: str | None = None
    normalization_reason = "No aplica a este tipo de entidad"
    variant_of: int | None = None
    merge_policy = "distinct"

    if ent.entity_type in _URL_TYPES:
        primary = ent.display_value or ent.normalized_value
        norm = normalize_url_for_entity(primary)
        canonical_key = norm.canonical_key
        normalization_reason = norm.normalization_reason
        with Session(engine) as session:
            peers = list(session.exec(select(Entity).where(Entity.case_id == case_id)).all())
        canonical_id: int | None = None
        for peer in peers:
            if peer.entity_type not in _URL_TYPES or int(peer.id or 0) == eid:
                continue
            peer_url = peer.display_value or peer.normalized_value
            if urls_are_equivalent(peer_url, primary):
                pid = int(peer.id or 0)
                if canonical_id is None or pid < canonical_id:
                    canonical_id = pid
        if canonical_id is not None and canonical_id != eid:
            variant_of = canonical_id
            merge_policy = "variant"
        elif canonical_id == eid:
            merge_policy = "canonical"

    review = reviews_by_entity(engine, case_id).get(eid)
    live_by = latest_checks_by_entity(engine, case_id)
    live_row = live_by.get(eid)

    is_wayback = ent.entity_type in _URL_TYPES and (
        "wayback" in sources or ent.entity_type == "archived_url"
    )
    wb_meta = (
        classify_wayback_url(ent.display_value or ent.normalized_value) if is_wayback else None
    )
    group_block: dict[str, Any] | None = None
    if wb_meta:
        group_block = {
            "key": wb_meta.group_key,
            "category": wb_meta.category,
            "priority": wb_meta.priority,
            "reason": wayback_group_reason(wb_meta),
            "non_destructive": True,
        }

    findings_out = [
        {
            "kind": f.kind,
            "value": f.value,
            "source": f.source,
            "confidence": f.confidence.value
            if hasattr(f.confidence, "value")
            else str(f.confidence),
            "normalized_data": dict(f.normalized_data) if f.normalized_data else {},
        }
        for f in related[:50]
    ]

    return {
        "entity_id": eid,
        "case_id": case_id,
        "entity_type": ent.entity_type,
        "display_value": ent.display_value,
        "normalized_value": norm.normalized_value if norm else ent.normalized_value,
        "original_values": original_values,
        "sources": sources,
        "source_names": sources,
        "evidence_ids": evidence_ids,
        "evidence_count": len(evidence_ids),
        "findings": findings_out,
        "group": group_block,
        "normalization": {
            "reason": normalization_reason,
            "canonical_key": canonical_key,
            "variant_of": variant_of,
            "merge_policy": merge_policy,
            "is_normalized_variant": norm.is_normalized_variant if norm else False,
        },
        "quality": None,
        "live_check": (
            {
                "status": live_row.get("status"),
                "status_code": live_row.get("status_code"),
                "final_url": live_row.get("final_url"),
                "checked_at": live_row.get("checked_at"),
            }
            if live_row
            else None
        ),
        "review": (
            {
                "review_status": review.review_status,
                "hidden": review.hidden,
                "hidden_reason": review.hidden_reason,
                "note": review.note,
            }
            if review
            else {"review_status": "pending", "hidden": False, "hidden_reason": None, "note": None}
        ),
    }
