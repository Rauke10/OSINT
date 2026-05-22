"""Persist scan findings as case entities and relationships."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from globeye.core.models import Finding, ScanResult, Target
from globeye.db.models import Entity, EntityRelationship
from globeye.services.url_normalization import normalize_url_for_entity

_URL_TYPES = frozenset({"url", "archived_url"})


def _normalize_key(entity_type: str, value: str) -> str:
    if entity_type in {"email", "domain", "subdomain", "username"}:
        return value.lower()
    if entity_type in _URL_TYPES:
        return normalize_url_for_entity(value).normalized_value
    return value


def persist_entities_from_scan(
    engine: Engine,
    *,
    case_id: int,
    job_id: int,
    result: ScanResult,
) -> tuple[int, int]:
    """Upsert entities and relationships from a scan. Returns (entities, relationships)."""
    now = datetime.now(UTC)
    root = result.target
    entity_count = 0
    rel_count = 0

    with Session(engine) as session:
        root_entity = _upsert_entity(
            session,
            case_id=case_id,
            job_id=job_id,
            entity_type=root.type.value,
            normalized_value=_normalize_key(root.type.value, root.value),
            display_value=root.value,
            now=now,
        )
        entity_count += 1
        id_by_key: dict[tuple[str, str], int] = {
            (root_entity.entity_type, root_entity.normalized_value): int(root_entity.id or 0)
        }

        for finding in result.findings:
            entities_created, rels_created = _process_finding(
                session,
                case_id=case_id,
                job_id=job_id,
                finding=finding,
                root=root,
                root_entity_id=int(root_entity.id or 0),
                id_by_key=id_by_key,
                now=now,
            )
            entity_count += entities_created
            rel_count += rels_created

        session.commit()

    return entity_count, rel_count


def _process_finding(
    session: Session,
    *,
    case_id: int,
    job_id: int,
    finding: Finding,
    root: Target,
    root_entity_id: int,
    id_by_key: dict[tuple[str, str], int],
    now: datetime,
) -> tuple[int, int]:
    entities_created = 0
    rels_created = 0
    hint = finding.graph_node_hint

    if finding.kind == "wayback_summary":
        return 0, 0

    if hint is not None:
        child_type = hint.node_type
        raw_url = hint.node_id or hint.label
        child_key = _normalize_key(child_type, raw_url)
        child_display = raw_url if child_type in _URL_TYPES else hint.label
        child = _upsert_entity(
            session,
            case_id=case_id,
            job_id=job_id,
            entity_type=child_type,
            normalized_value=child_key,
            display_value=child_display,
            now=now,
        )
        key = (child_type, child_key)
        if key not in id_by_key:
            entities_created += 1
        id_by_key[key] = int(child.id or 0)

        parent_id_str = hint.parent_id or root.value
        parent_type = _infer_parent_type(parent_id_str, root)
        parent_key = _normalize_key(parent_type, parent_id_str)
        parent = _upsert_entity(
            session,
            case_id=case_id,
            job_id=job_id,
            entity_type=parent_type,
            normalized_value=parent_key,
            display_value=parent_id_str,
            now=now,
        )
        pkey = (parent_type, parent_key)
        if pkey not in id_by_key:
            entities_created += 1
        id_by_key[pkey] = int(parent.id or 0)

        if int(parent.id or 0) != int(child.id or 0) and _upsert_relationship(
            session,
            case_id=case_id,
            source_entity_id=int(parent.id or 0),
            target_entity_id=int(child.id or 0),
            relationship_type="discovered_via",
            source_name=finding.source,
            now=now,
        ):
            rels_created += 1
        return entities_created, rels_created

    child_type = finding.kind
    child_key = _normalize_key(child_type, finding.value)
    child_display = finding.value
    child = _upsert_entity(
        session,
        case_id=case_id,
        job_id=job_id,
        entity_type=child_type,
        normalized_value=child_key,
        display_value=child_display,
        now=now,
    )
    key = (child_type, child_key)
    if key not in id_by_key:
        entities_created += 1
    id_by_key[key] = int(child.id or 0)

    if int(child.id or 0) != root_entity_id and _upsert_relationship(
        session,
        case_id=case_id,
        source_entity_id=root_entity_id,
        target_entity_id=int(child.id or 0),
        relationship_type="discovered_via",
        source_name=finding.source,
        now=now,
    ):
        rels_created += 1

    return entities_created, rels_created


def _infer_parent_type(parent_id: str, root: Target) -> str:
    if parent_id == root.value:
        return root.type.value
    if "." in parent_id and "@" not in parent_id:
        return "domain"
    return root.type.value


def _upsert_entity(
    session: Session,
    *,
    case_id: int,
    job_id: int,
    entity_type: str,
    normalized_value: str,
    display_value: str,
    now: datetime,
) -> Entity:
    stmt = select(Entity).where(
        Entity.case_id == case_id,
        Entity.entity_type == entity_type,
        Entity.normalized_value == normalized_value,
    )
    existing = session.exec(stmt).first()
    if existing is not None:
        existing.last_seen_at = now
        existing.last_job_id = job_id
        if display_value and len(display_value) > len(existing.display_value):
            existing.display_value = display_value[:512]
        session.add(existing)
        return existing

    entity = Entity(
        case_id=case_id,
        entity_type=entity_type,
        normalized_value=normalized_value,
        display_value=display_value[:512],
        first_seen_at=now,
        last_seen_at=now,
        last_job_id=job_id,
    )
    session.add(entity)
    session.flush()
    return entity


def _upsert_relationship(
    session: Session,
    *,
    case_id: int,
    source_entity_id: int,
    target_entity_id: int,
    relationship_type: str,
    source_name: str,
    now: datetime,
) -> bool:
    if source_entity_id == target_entity_id:
        return False
    stmt = select(EntityRelationship).where(
        EntityRelationship.case_id == case_id,
        EntityRelationship.source_entity_id == source_entity_id,
        EntityRelationship.target_entity_id == target_entity_id,
        EntityRelationship.relationship_type == relationship_type,
        EntityRelationship.source_name == source_name,
    )
    if session.exec(stmt).first() is not None:
        return False
    session.add(
        EntityRelationship(
            case_id=case_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            source_name=source_name,
            created_at=now,
        )
    )
    return True


def build_case_graph(
    engine: Engine,
    case_id: int,
    *,
    mode: str = "inventory",
) -> dict[str, list[dict[str, Any]]]:
    """Build cytoscape-compatible nodes/edges; default mode shows approved inventory only."""
    from globeye.services.entity_review import reviews_by_entity
    from globeye.services.url_live_check import latest_checks_by_entity

    review_by_entity = reviews_by_entity(engine, case_id)
    live_by_entity = latest_checks_by_entity(engine, case_id)
    approved_ids = {
        eid
        for eid, rev in review_by_entity.items()
        if rev.approved_for_inventory and not rev.hidden
    }

    with Session(engine) as session:
        entities = list(session.exec(select(Entity).where(Entity.case_id == case_id)).all())
        relationships = list(
            session.exec(
                select(EntityRelationship).where(EntityRelationship.case_id == case_id)
            ).all()
        )

    if mode == "inventory":
        entities = [e for e in entities if int(e.id or 0) in approved_ids]
    elif mode == "live":
        live_ids = {
            eid
            for eid, row in live_by_entity.items()
            if str(row.get("status")) in {"live_200", "redirect"}
        }
        entities = [e for e in entities if int(e.id or 0) in live_ids]
    elif mode == "high":
        entities = [
            e
            for e in entities
            if int(e.id or 0) in approved_ids
            and (
                review_by_entity.get(int(e.id or 0))
                and review_by_entity[int(e.id or 0)].inventory_priority
            )
            in {"high", "critical"}
        ]
    # mode == "all" keeps every entity

    allowed = {str(int(e.id or 0)) for e in entities}
    nodes: dict[str, dict[str, Any]] = {}
    for ent in entities:
        eid = str(ent.id)
        nodes[eid] = {
            "data": {
                "id": eid,
                "label": ent.display_value[:38],
                "type": ent.entity_type,
                "value": ent.normalized_value,
            }
        }

    edges: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rel in relationships:
        sid = str(rel.source_entity_id)
        tid = str(rel.target_entity_id)
        if sid not in allowed or tid not in allowed:
            continue
        edge_id = f"{sid}->{tid}:{rel.source_name}"
        if edge_id in seen or sid == tid:
            continue
        seen.add(edge_id)
        edges.append(
            {
                "data": {
                    "id": edge_id,
                    "source": sid,
                    "target": tid,
                    "via": rel.source_name,
                    "relationship_type": rel.relationship_type,
                }
            }
        )

    return {"nodes": list(nodes.values()), "edges": edges}
