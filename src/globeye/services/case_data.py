"""Case data explorer: aggregated entities, sources, evidence (Fase 2C / 2C.3)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

from globeye.core.models import Finding
from globeye.db.models import Entity, EntityRelationship, StoredEvidence
from globeye.services.entity_review import inventory_fields_from_review, reviews_by_entity
from globeye.services.entity_trace import _original_values_for_entity, _related_findings
from globeye.services.finding_quality import (
    FindingQualityMeta,
    QualityLabel,
    _entity_key,
    _source_groups,
    classify_entity_from_findings,
    classify_finding,
    load_case_findings,
)
from globeye.services.operational_status import compute_operational_status, operational_summary
from globeye.services.url_grouping import (
    classify_wayback_url,
    wayback_group_reason,
    wayback_group_summary,
)
from globeye.services.url_live_check import MAX_BATCH_URLS as WAYBACK_LIVE_CHECK_BATCH_LIMIT
from globeye.services.url_live_check import latest_checks_by_entity, live_quality_reason
from globeye.services.url_normalization import normalize_url_for_entity
from globeye.sources.infra.wayback import CDX_FETCH_LIMIT, WAYBACK_FINDINGS_PER_SCAN

_URL_ENTITY_TYPES = frozenset({"url", "archived_url"})

EXPLORER_TYPES = frozenset(
    {
        "domain",
        "subdomain",
        "ip",
        "email",
        "url",
        "username",
        "phone",
        "person",
        "organization",
        "document",
        "certificate",
    }
)

_TYPE_ALIASES: dict[str, str] = {
    "org": "organization",
    "registration": "domain",
    "service": "ip",
    "archived_url": "url",
    "cert_hash": "certificate",
}


def explorer_type(entity_type: str) -> str:
    return _TYPE_ALIASES.get(entity_type, entity_type)


def _keys_for_finding(finding: Finding) -> list[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    if finding.graph_node_hint is not None:
        h = finding.graph_node_hint
        keys.add((h.node_type, _entity_key(h.node_type, h.node_id)[1]))
    keys.add(_entity_key(finding.kind, finding.value))
    return list(keys)


def _build_quality_and_sources(
    engine: Engine, case_id: int
) -> tuple[dict[tuple[str, str], FindingQualityMeta], dict[tuple[str, str], set[str]]]:
    pairs = load_case_findings(engine, case_id)
    all_findings = [f for f, _ in pairs]
    groups = _source_groups(all_findings)
    wayback_total = sum(1 for f in all_findings if f.kind == "archived_url")
    metas_by_key: dict[tuple[str, str], list[FindingQualityMeta]] = defaultdict(list)
    sources_by_key: dict[tuple[str, str], set[str]] = defaultdict(set)

    for finding, target in pairs:
        for key in _keys_for_finding(finding):
            sources_by_key[key].add(finding.source)
            metas_by_key[key].append(
                classify_finding(
                    finding,
                    target=target,
                    source_counts=groups,
                    wayback_total=wayback_total,
                )
            )

    quality_by_key: dict[tuple[str, str], FindingQualityMeta] = {}
    for key, metas in metas_by_key.items():
        etype, nval = key
        quality_by_key[key] = classify_entity_from_findings(etype, nval, metas)
    return quality_by_key, sources_by_key


def _relationship_sources(session: Session, case_id: int) -> dict[int, set[str]]:
    by_entity: dict[int, set[str]] = defaultdict(set)
    for rel in session.exec(
        select(EntityRelationship).where(EntityRelationship.case_id == case_id)
    ).all():
        by_entity[int(rel.source_entity_id)].add(rel.source_name)
        by_entity[int(rel.target_entity_id)].add(rel.source_name)
    return by_entity


def _evidence_ids_by_entity(session: Session, case_id: int) -> dict[int, list[int]]:
    rows = session.exec(
        select(StoredEvidence.entity_id, StoredEvidence.id)
        .where(StoredEvidence.case_id == case_id)
        .where(col(StoredEvidence.entity_id).isnot(None))
        .order_by(col(StoredEvidence.id))
    ).all()
    out: dict[int, list[int]] = defaultdict(list)
    for eid, evid in rows:
        if eid is not None and evid is not None:
            out[int(eid)].append(int(evid))
    return dict(out)


def _canonical_variant_map(entities: list[Entity]) -> dict[int, int | None]:
    """Map entity_id -> canonical entity_id for equivalent URLs, else None."""
    owners: dict[str, int] = {}
    variant_of: dict[int, int | None] = {}
    for ent in entities:
        if ent.entity_type not in _URL_ENTITY_TYPES:
            variant_of[int(ent.id or 0)] = None
            continue
        url = ent.display_value or ent.normalized_value
        ck = normalize_url_for_entity(url).canonical_key
        eid = int(ent.id or 0)
        if ck not in owners:
            owners[ck] = eid
            variant_of[eid] = None
        elif owners[ck] == eid:
            variant_of[eid] = None
        else:
            variant_of[eid] = owners[ck]
    return variant_of


def _evidence_stats(session: Session, case_id: int) -> dict[int, tuple[int, int | None]]:
    rows = session.exec(
        select(
            StoredEvidence.entity_id,
            func.count(col(StoredEvidence.id)),
            func.min(StoredEvidence.scan_job_id),
        )
        .where(StoredEvidence.case_id == case_id)
        .where(col(StoredEvidence.entity_id).isnot(None))
        .group_by(col(StoredEvidence.entity_id))
    ).all()
    return {
        int(eid): (int(cnt), int(min_job) if min_job is not None else None)
        for eid, cnt, min_job in rows
        if eid is not None
    }


def _passes_filters(
    item: dict[str, Any],
    *,
    type_filter: str | None,
    quality_filter: str | None,
    source_filter: str | None,
    query: str | None,
    hide_noisy: bool,
    hide_historical: bool,
    hide_false_positive: bool,
    verified_only: bool,
    live_status_filter: str | None = None,
    hide_discarded: bool = False,
    review_status_filter: str | None = None,
    wayback_category: str | None = None,
    wayback_priority: str | None = None,
    operational_status_filter: str | None = None,
    only_high_priority: bool = False,
    inventory_status_filter: str | None = None,
) -> bool:
    if hide_discarded and item.get("hidden"):
        return False
    if (
        review_status_filter
        and review_status_filter != "all"
        and item.get("review_status") != review_status_filter
    ):
        return False
    if type_filter and type_filter != "all" and item["type"] != type_filter:
        return False
    label = item.get("quality_label") or ""
    if quality_filter and quality_filter != "all" and label != quality_filter:
        return False
    if verified_only and label not in {
        QualityLabel.VERIFIED.value,
        QualityLabel.LIKELY.value,
    }:
        return False
    if hide_historical and (label == QualityLabel.HISTORICAL.value or item.get("is_historical")):
        return False
    if hide_noisy and label == QualityLabel.NOISY.value:
        return False
    if hide_false_positive and (
        label == QualityLabel.POSSIBLE_FALSE_POSITIVE.value
        or item.get("is_potential_false_positive")
    ):
        return False
    if source_filter and source_filter not in item.get("sources", []):
        return False
    if query:
        q = query.lower()
        blob = " ".join(
            [
                item["type"],
                item["value"],
                item.get("display_value", ""),
                " ".join(item.get("sources", [])),
            ]
        )
        if q not in blob.lower():
            return False
    if live_status_filter and live_status_filter != "all":
        if live_status_filter == "discarded":
            if not item.get("hidden") and item.get("review_status") != "discarded":
                return False
        else:
            current = item.get("live_status") or "not_checked"
            if live_status_filter == "not_checked":
                if current != "not_checked":
                    return False
            elif current != live_status_filter:
                return False
    if wayback_category and item.get("wayback_category") != wayback_category:
        return False
    if wayback_priority and item.get("wayback_priority") != wayback_priority:
        return False
    if only_high_priority and item.get("wayback_priority") != "high":
        return False
    if (
        operational_status_filter
        and operational_status_filter != "all"
        and item.get("operational_status") != operational_status_filter
    ):
        return False
    if inventory_status_filter and inventory_status_filter != "all":
        approved = bool(item.get("approved_for_inventory"))
        inv = str(item.get("inventory_status") or "candidate")
        hidden = bool(item.get("hidden"))
        if inventory_status_filter == "pending":
            if approved or hidden:
                return False
        elif inventory_status_filter == "approved":
            if not approved or hidden or inv != "approved":
                return False
        elif inventory_status_filter == "not_approved":
            if approved:
                return False
        elif inventory_status_filter == "discarded":
            if not hidden:
                return False
        elif (
            inventory_status_filter in {"candidate", "rejected"} and inv != inventory_status_filter
        ):
            return False
    return True


def build_case_data(
    engine: Engine,
    case_id: int,
    *,
    type_filter: str | None = None,
    quality_filter: str | None = None,
    source_filter: str | None = None,
    query: str | None = None,
    hide_noisy: bool = False,
    hide_historical: bool = False,
    hide_false_positive: bool = False,
    verified_only: bool = False,
    live_status_filter: str | None = None,
    hide_discarded: bool = False,
    review_status_filter: str | None = None,
    wayback_category: str | None = None,
    wayback_priority: str | None = None,
    operational_status_filter: str | None = None,
    only_high_priority: bool = False,
    inventory_status_filter: str | None = "pending",
    limit: int = 500,
    offset: int = 0,
    debug_timing: bool = False,
) -> dict[str, Any]:
    """Build explorer payload with summary, filters, and Wayback grouping."""
    import time as _time

    t0 = _time.perf_counter()
    limit = min(max(limit, 1), 2000)
    offset = max(offset, 0)
    if inventory_status_filter is None:
        inventory_status_filter = "pending"

    quality_by_key, finding_sources = _build_quality_and_sources(engine, case_id)
    live_by_entity = latest_checks_by_entity(engine, case_id)
    review_by_entity = reviews_by_entity(engine, case_id)

    with Session(engine) as session:
        entities = list(
            session.exec(
                select(Entity)
                .where(Entity.case_id == case_id)
                .order_by(col(Entity.last_seen_at).desc(), col(Entity.id).desc())
            ).all()
        )
        rel_sources = _relationship_sources(session, case_id)
        ev_stats = _evidence_stats(session, case_id)
        ev_ids_by_entity = _evidence_ids_by_entity(session, case_id)
        total_evidence = int(
            session.exec(
                select(func.count(col(StoredEvidence.id))).where(StoredEvidence.case_id == case_id)
            ).one()
            or 0
        )
        wayback_evidence_count = int(
            session.exec(
                select(func.count(col(StoredEvidence.id)))
                .where(StoredEvidence.case_id == case_id)
                .where(
                    or_(
                        col(StoredEvidence.finding_kind) == "archived_url",
                        col(StoredEvidence.source_name) == "wayback",
                    )
                )
            ).one()
            or 0
        )

    pairs = load_case_findings(engine, case_id)
    total_findings = len(pairs)
    findings_only = [f for f, _ in pairs]
    variant_of_map = _canonical_variant_map(entities)

    all_items: list[dict[str, Any]] = []
    summary: dict[str, int] = defaultdict(int)

    for ent in entities:
        eid = int(ent.id or 0)
        etype = explorer_type(ent.entity_type)
        key = (ent.entity_type, ent.normalized_value)
        qmeta = quality_by_key.get(key)
        if qmeta is None:
            for alt_key in _keys_matching_entity(ent):
                qmeta = quality_by_key.get(alt_key)
                if qmeta is not None:
                    break
        if qmeta is None:
            qmeta = FindingQualityMeta(
                quality_label=QualityLabel.UNVERIFIED.value,
                confidence_score=40,
                quality_reason="Sin hallazgos vinculados en escaneos",
            )

        srcs = set(rel_sources.get(eid, set()))
        srcs.update(finding_sources.get(key, set()))
        for alt in _keys_matching_entity(ent):
            srcs.update(finding_sources.get(alt, set()))

        ev_count, first_job = ev_stats.get(eid, (0, None))
        first_job_id = first_job if first_job is not None else ent.last_job_id

        is_wayback_url = etype == "url" and (
            "wayback" in srcs or qmeta.is_historical or ent.entity_type == "archived_url"
        )
        is_web_checkable = etype in {"url", "domain", "subdomain"}
        live_row = live_by_entity.get(eid) if is_web_checkable else None
        live_status = (
            str(live_row["status"]) if live_row else ("not_checked" if is_web_checkable else None)
        )
        quality_reason = qmeta.quality_reason
        if is_wayback_url and live_row:
            extra = live_quality_reason(str(live_row["status"]))
            if extra:
                quality_reason = f"{quality_reason}; {extra}" if quality_reason else extra

        review = review_by_entity.get(eid)
        url_for_group = ent.display_value or ent.normalized_value
        wb_meta = classify_wayback_url(url_for_group) if is_wayback_url else None
        evidence_ids = ev_ids_by_entity.get(eid, [])
        original_values = [ent.display_value or ent.normalized_value]

        norm_result = None
        canonical_key: str | None = None
        normalization_reason = "Entidad no URL; valor normalizado = clave almacenada"
        group_reason: str | None = None
        if ent.entity_type in _URL_ENTITY_TYPES:
            norm_result = normalize_url_for_entity(url_for_group)
            canonical_key = norm_result.canonical_key
            normalization_reason = norm_result.normalization_reason
            if wb_meta:
                group_reason = wayback_group_reason(wb_meta)

        item: dict[str, Any] = {
            "id": eid,
            "type": etype,
            "entity_type": ent.entity_type,
            "value": ent.normalized_value,
            "display_value": ent.display_value,
            "quality_label": qmeta.quality_label,
            "confidence_score": qmeta.confidence_score,
            "verification_sources_count": qmeta.verification_sources_count,
            "is_historical": qmeta.is_historical,
            "is_potential_false_positive": qmeta.is_potential_false_positive,
            "quality_reason": quality_reason,
            "sources": sorted(srcs),
            "evidence_count": ev_count,
            "first_seen_at": ent.first_seen_at.isoformat(),
            "last_seen_at": ent.last_seen_at.isoformat(),
            "first_job_id": first_job_id,
            "last_job_id": ent.last_job_id,
            "is_wayback_url": is_wayback_url,
            "live_status": live_status,
            "live_checked_at": live_row.get("checked_at") if live_row else None,
            "last_live_checked_at": live_row.get("checked_at") if live_row else None,
            "live_status_code": live_row.get("status_code") if live_row else None,
            "live_final_url": live_row.get("final_url") if live_row else None,
            "live_check_id": live_row.get("id") if live_row else None,
            "review_status": review.review_status if review else "pending",
            "hidden": review.hidden if review else False,
            "hidden_reason": review.hidden_reason if review else None,
            "review_note": review.note if review else None,
            **inventory_fields_from_review(review),
            "inventory_suggested": bool(
                is_wayback_url
                and live_status in {"live_200", "redirect"}
                and not (review and review.approved_for_inventory)
            ),
            "wayback_category": wb_meta.category if wb_meta else None,
            "wayback_priority": wb_meta.priority if wb_meta else None,
            "wayback_group_key": wb_meta.group_key if wb_meta else None,
            "normalized_value": (
                norm_result.normalized_value if norm_result else ent.normalized_value
            ),
            "original_values": original_values,
            "canonical_key": canonical_key,
            "variant_of": variant_of_map.get(eid),
            "normalization_reason": normalization_reason,
            "group_key": wb_meta.group_key if wb_meta else None,
            "group_reason": group_reason,
            "evidence_ids": evidence_ids,
            "source_names": sorted(srcs),
        }
        item["operational_status"] = compute_operational_status(item)
        all_items.append(item)

        summary[etype] = summary.get(etype, 0) + 1
        summary[qmeta.quality_label] = summary.get(qmeta.quality_label, 0) + 1
        if qmeta.quality_label in {QualityLabel.VERIFIED.value, QualityLabel.LIKELY.value}:
            summary["verified_or_likely"] = summary.get("verified_or_likely", 0) + 1
        if qmeta.quality_label in {QualityLabel.HISTORICAL.value, QualityLabel.NOISY.value}:
            summary["historical_or_noisy"] = summary.get("historical_or_noisy", 0) + 1
        if qmeta.is_potential_false_positive:
            summary["possible_false_positive"] = summary.get("possible_false_positive", 0) + 1

    summary["finding"] = total_findings
    summary["evidence"] = int(total_evidence or 0)
    summary["total_items"] = len(all_items)
    summary.update(operational_summary(all_items))

    filtered = [
        it
        for it in all_items
        if _passes_filters(
            it,
            type_filter=type_filter,
            quality_filter=quality_filter,
            source_filter=source_filter,
            query=query,
            hide_noisy=hide_noisy,
            hide_historical=hide_historical,
            hide_false_positive=hide_false_positive,
            verified_only=verified_only,
            live_status_filter=live_status_filter,
            hide_discarded=hide_discarded,
            review_status_filter=review_status_filter,
            wayback_category=wayback_category,
            wayback_priority=wayback_priority,
            operational_status_filter=operational_status_filter,
            only_high_priority=only_high_priority,
            inventory_status_filter=inventory_status_filter,
        )
    ]

    filtered_ids = {it["id"] for it in filtered}
    hidden_noisy = sum(
        1
        for it in all_items
        if it["id"] not in filtered_ids
        and it.get("quality_label") == QualityLabel.NOISY.value
        and hide_noisy
    )
    hidden_historical = sum(
        1
        for it in all_items
        if it["id"] not in filtered_ids
        and (it.get("quality_label") == QualityLabel.HISTORICAL.value or it.get("is_historical"))
        and hide_historical
    )
    hidden_discarded = sum(
        1
        for it in all_items
        if it["id"] not in filtered_ids and it.get("hidden") and hide_discarded
    )
    hidden_fp = sum(
        1
        for it in all_items
        if it["id"] not in filtered_ids
        and (
            it.get("quality_label") == QualityLabel.POSSIBLE_FALSE_POSITIVE.value
            or it.get("is_potential_false_positive")
        )
        and hide_false_positive
    )
    total_count = len(all_items)
    filtered_count = len(filtered)
    hidden_by_filters_count = total_count - filtered_count
    page = filtered[offset : offset + limit]
    page_ids = {int(it["id"]) for it in page}
    for ent in entities:
        eid = int(ent.id or 0)
        if eid not in page_ids:
            continue
        for it in page:
            if it["id"] != eid:
                continue
            related = _related_findings(
                pairs, ent.entity_type, ent.normalized_value, ent.display_value
            )
            it["original_values"] = _original_values_for_entity(ent, related, [])
            break
    archived_url_findings = sum(1 for f in findings_only if f.kind == "archived_url")
    url_entity_count = sum(1 for it in all_items if it["type"] == "url")
    wayback_items = [it for it in all_items if it.get("is_wayback_url")]
    wayback_filtered = [it for it in filtered if it.get("is_wayback_url")]
    wayback_visible_ids = {it["id"] for it in filtered}
    wayback_hidden_by_filters = sum(
        1 for it in wayback_items if it["id"] not in wayback_visible_ids
    )

    counts = {
        "total_count": total_count,
        "filtered_count": filtered_count,
        "visible_count": len(page),
        "hidden_by_filters_count": hidden_by_filters_count,
        "hidden_noisy_count": hidden_noisy,
        "hidden_historical_count": hidden_historical,
        "hidden_discarded_count": hidden_discarded,
        "hidden_false_positive_count": hidden_fp,
        "discarded_count": sum(1 for it in all_items if it.get("hidden")),
        "historical_count": sum(
            1
            for it in all_items
            if it.get("quality_label") == QualityLabel.HISTORICAL.value or it.get("is_historical")
        ),
        "noisy_count": sum(
            1 for it in all_items if it.get("quality_label") == QualityLabel.NOISY.value
        ),
        "false_positive_count": sum(
            1
            for it in all_items
            if it.get("quality_label") == QualityLabel.POSSIBLE_FALSE_POSITIVE.value
            or it.get("is_potential_false_positive")
        ),
        "evidence_total_count": int(total_evidence or 0),
        "evidence_filtered_count": sum(it.get("evidence_count", 0) for it in filtered),
        "findings_total_count": total_findings,
        "archived_url_findings_count": archived_url_findings,
        "url_entity_count": url_entity_count,
        "wayback_entity_limit": WAYBACK_LIVE_CHECK_BATCH_LIMIT,
        "wayback_live_check_batch_limit": WAYBACK_LIVE_CHECK_BATCH_LIMIT,
        "wayback_scan_url_cap": WAYBACK_FINDINGS_PER_SCAN,
        "wayback_cdx_fetch_limit": CDX_FETCH_LIMIT,
        "max_api_limit": 2000,
        "wayback_original_total": archived_url_findings,
        "wayback_evidence_count": wayback_evidence_count,
        "wayback_entity_count": url_entity_count,
        "wayback_grouped_count": len(wayback_items),
        "wayback_visible_count": len(wayback_filtered),
        "wayback_hidden_by_filters_count": wayback_hidden_by_filters,
        "wayback_discarded_count": sum(1 for it in wayback_items if it.get("hidden")),
        "wayback_live_200_count": sum(
            1 for it in wayback_items if str(it.get("live_status")) in {"live_200", "redirect"}
        ),
        "wayback_404_count": sum(
            1 for it in wayback_items if str(it.get("live_status")) == "not_found"
        ),
        "wayback_pending_live_count": sum(
            1
            for it in wayback_items
            if str(it.get("live_status") or "not_checked") == "not_checked"
        ),
    }

    timing_ms: dict[str, float] | None = None
    if debug_timing:
        timing_ms = {
            "total_ms": round((_time.perf_counter() - t0) * 1000, 2),
            "entities_scanned": float(len(entities)),
            "rows_returned": float(len(page)),
            "filtered_count": float(filtered_count),
        }

    return {
        "summary": dict(summary),
        "timing_ms": timing_ms,
        "counts": counts,
        "operational_summary": operational_summary(all_items),
        "wayback_groups": wayback_group_summary(filtered),
        "inventory_approved_count": sum(1 for it in all_items if it.get("approved_for_inventory")),
        "inventory_candidate_count": sum(
            1 for it in all_items if (it.get("inventory_status") or "candidate") == "candidate"
        ),
        "items": page,
        "total": filtered_count,
        "total_count": total_count,
        "visible_count": len(page),
        "filtered_count": filtered_count,
        "hidden_by_filters_count": hidden_by_filters_count,
        "total_filtered": filtered_count,
        "offset": offset,
        "limit": limit,
        "hidden_noisy_count": hidden_noisy + hidden_historical,
        "hidden_historical_count": hidden_historical,
        "hidden_discarded_count": hidden_discarded,
        "evidence_total_count": int(total_evidence or 0),
        "evidence_visible_count": sum(it.get("evidence_count", 0) for it in page),
        "findings_total_count": total_findings,
    }


def _keys_matching_entity(ent: Entity) -> list[tuple[str, str]]:
    keys = [(ent.entity_type, ent.normalized_value)]
    if ent.entity_type == "url":
        keys.append(("archived_url", ent.normalized_value))
    return keys
