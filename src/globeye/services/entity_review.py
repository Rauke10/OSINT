"""Entity/evidence review, discard, and inventory (Fase 2C.3 / 2D)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

from globeye.db.models import Entity, EntityReview, StoredEvidence
from globeye.db.models.entity_review import INVENTORY_PRIORITIES, INVENTORY_STATUSES

REVIEW_STATUSES = frozenset({"pending", "reviewed", "discarded", "false_positive"})


def inventory_fields_from_review(row: EntityReview | None) -> dict[str, Any]:
    if row is None:
        return {
            "approved_for_inventory": False,
            "inventory_status": "candidate",
            "inventory_priority": None,
            "inventory_note": None,
            "approved_at": None,
            "approved_reason": None,
        }
    return {
        "approved_for_inventory": bool(row.approved_for_inventory),
        "inventory_status": row.inventory_status or "candidate",
        "inventory_priority": row.inventory_priority,
        "inventory_note": row.inventory_note,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
        "approved_reason": row.approved_reason,
    }


def _find_existing(
    session: Session,
    case_id: int,
    *,
    entity_id: int | None,
    evidence_id: int | None,
    value: str | None,
) -> EntityReview | None:
    if entity_id is not None:
        row = session.exec(
            select(EntityReview)
            .where(EntityReview.case_id == case_id)
            .where(EntityReview.entity_id == entity_id)
            .order_by(col(EntityReview.updated_at).desc())
        ).first()
        if row:
            return row
    if evidence_id is not None:
        row = session.exec(
            select(EntityReview)
            .where(EntityReview.case_id == case_id)
            .where(EntityReview.evidence_id == evidence_id)
            .order_by(col(EntityReview.updated_at).desc())
        ).first()
        if row:
            return row
    if value:
        norm = value.strip().lower()[:2048]
        for row in session.exec(select(EntityReview).where(EntityReview.case_id == case_id)).all():
            if row.value and row.value.strip().lower() == norm:
                return row
    return None


def reviews_by_entity(engine: Engine, case_id: int) -> dict[int, EntityReview]:
    with Session(engine) as session:
        rows = list(session.exec(select(EntityReview).where(EntityReview.case_id == case_id)).all())
    by_entity: dict[int, EntityReview] = {}
    for row in rows:
        if row.entity_id is not None:
            eid = int(row.entity_id)
            prev = by_entity.get(eid)
            if prev is None or (
                row.updated_at and prev.updated_at and row.updated_at >= prev.updated_at
            ):
                by_entity[eid] = row
    return by_entity


def reviews_by_evidence(engine: Engine, case_id: int) -> dict[int, EntityReview]:
    with Session(engine) as session:
        rows = list(session.exec(select(EntityReview).where(EntityReview.case_id == case_id)).all())
    out: dict[int, EntityReview] = {}
    for row in rows:
        if row.evidence_id is not None:
            out[int(row.evidence_id)] = row
    return out


def review_to_dict(row: EntityReview) -> dict[str, Any]:
    base = {
        "id": int(row.id or 0),
        "case_id": row.case_id,
        "entity_id": row.entity_id,
        "evidence_id": row.evidence_id,
        "value": row.value,
        "review_status": row.review_status,
        "hidden": row.hidden,
        "hidden_reason": row.hidden_reason,
        "note": row.note,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }
    base.update(inventory_fields_from_review(row))
    return base


def _apply_approved_state(row: EntityReview, now: datetime, *, approved_reason: str | None) -> None:
    row.approved_for_inventory = True
    row.inventory_status = "approved"
    row.review_status = "reviewed"
    row.hidden = False
    row.hidden_reason = None
    row.approved_at = now
    if approved_reason is not None:
        row.approved_reason = approved_reason


def _apply_discarded_state(row: EntityReview, *, hidden_reason: str | None) -> None:
    row.approved_for_inventory = False
    row.inventory_status = "rejected"
    row.review_status = "discarded"
    row.hidden = True
    row.hidden_reason = hidden_reason
    row.approved_at = None
    row.approved_reason = None


def _apply_pending_state(row: EntityReview) -> None:
    row.approved_for_inventory = False
    row.inventory_status = "candidate"
    row.review_status = "pending"
    row.hidden = False
    row.hidden_reason = None
    row.approved_at = None
    row.approved_reason = None


def _apply_restored_state(row: EntityReview) -> None:
    row.hidden = False
    row.hidden_reason = None
    if row.approved_for_inventory:
        row.review_status = "reviewed"
        row.inventory_status = "approved"
    else:
        row.review_status = "pending"
        if row.inventory_status == "rejected":
            row.inventory_status = "candidate"


def upsert_review(
    engine: Engine,
    case_id: int,
    *,
    entity_id: int | None = None,
    evidence_id: int | None = None,
    value: str | None = None,
    review_status: str | None = None,
    hidden: bool | None = None,
    hidden_reason: str | None = None,
    note: str | None = None,
    approved_for_inventory: bool | None = None,
    inventory_status: str | None = None,
    inventory_priority: str | None = None,
    inventory_note: str | None = None,
    approved_reason: str | None = None,
    clear_approval: bool = False,
    force_clear_hidden: bool = False,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    with Session(engine) as session:
        row = _find_existing(
            session, case_id, entity_id=entity_id, evidence_id=evidence_id, value=value
        )
        if row is None:
            if entity_id and value is None:
                ent = session.get(Entity, entity_id)
                if ent:
                    value = ent.normalized_value
            if approved_for_inventory:
                rs = "reviewed"
                inv_status = "approved"
                hid = False
                hid_reason = None
                appr = True
            elif clear_approval or (review_status == "discarded"):
                appr = False
                rs = review_status if review_status in REVIEW_STATUSES else "discarded"
                inv_status = "rejected" if review_status == "discarded" else "candidate"
                hid = hidden if hidden is not None else review_status == "discarded"
                hid_reason = hidden_reason
            else:
                rs = review_status if review_status in REVIEW_STATUSES else "pending"
                inv_status = (
                    inventory_status if inventory_status in INVENTORY_STATUSES else "candidate"
                )
                hid = hidden if hidden is not None else False
                hid_reason = hidden_reason
                appr = bool(approved_for_inventory)
            row = EntityReview(
                case_id=case_id,
                entity_id=entity_id,
                evidence_id=evidence_id,
                value=value,
                review_status=rs,
                hidden=hid,
                hidden_reason=hid_reason,
                note=note,
                approved_for_inventory=appr,
                inventory_status=inv_status,
                inventory_priority=inventory_priority,
                inventory_note=inventory_note,
                approved_at=now if appr else None,
                approved_reason=approved_reason if appr else None,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
        else:
            if approved_for_inventory:
                _apply_approved_state(row, now, approved_reason=approved_reason)
            elif review_status == "discarded" or hidden is True:
                _apply_discarded_state(row, hidden_reason=hidden_reason)
            elif clear_approval:
                _apply_pending_state(row)
            elif force_clear_hidden or hidden is False:
                _apply_restored_state(row)
                if review_status is not None and review_status in REVIEW_STATUSES:
                    row.review_status = review_status
            else:
                if review_status is not None and review_status in REVIEW_STATUSES:
                    row.review_status = review_status
                if hidden_reason is not None:
                    row.hidden_reason = hidden_reason
                if inventory_status is not None and inventory_status in INVENTORY_STATUSES:
                    row.inventory_status = inventory_status
                if approved_for_inventory is not None:
                    row.approved_for_inventory = approved_for_inventory
            if note is not None:
                row.note = note
            if inventory_note is not None:
                row.inventory_note = inventory_note
            if inventory_priority is not None and (
                inventory_priority in INVENTORY_PRIORITIES or inventory_priority == ""
            ):
                row.inventory_priority = inventory_priority or None
            if approved_reason is not None and row.approved_for_inventory:
                row.approved_reason = approved_reason
            row.updated_at = now
            session.add(row)
        session.commit()
        session.refresh(row)
    return review_to_dict(row)


def approve_entities(
    engine: Engine,
    case_id: int,
    entity_ids: list[int],
    *,
    inventory_priority: str | None = None,
    inventory_note: str | None = None,
    approved_reason: str | None = None,
) -> dict[str, Any]:
    updated: list[dict[str, Any]] = []
    for eid in entity_ids:
        updated.append(
            upsert_review(
                engine,
                case_id,
                entity_id=eid,
                approved_for_inventory=True,
                inventory_status="approved",
                inventory_priority=inventory_priority,
                inventory_note=inventory_note,
                approved_reason=approved_reason,
                force_clear_hidden=True,
            )
        )
    return {"updated": len(updated), "reviews": updated}


def discard_entities(
    engine: Engine,
    case_id: int,
    entity_ids: list[int],
    *,
    hidden_reason: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    updated: list[dict[str, Any]] = []
    for eid in entity_ids:
        updated.append(
            upsert_review(
                engine,
                case_id,
                entity_id=eid,
                review_status="discarded",
                hidden=True,
                hidden_reason=hidden_reason,
                note=note,
                approved_for_inventory=False,
                inventory_status="rejected",
            )
        )
    return {"updated": len(updated), "reviews": updated}


def remove_from_inventory(
    engine: Engine,
    case_id: int,
    entity_ids: list[int],
) -> dict[str, Any]:
    updated: list[dict[str, Any]] = []
    for eid in entity_ids:
        updated.append(
            upsert_review(
                engine,
                case_id,
                entity_id=eid,
                clear_approval=True,
                force_clear_hidden=True,
            )
        )
    return {"updated": len(updated), "reviews": updated}


def restore_entities(
    engine: Engine,
    case_id: int,
    entity_ids: list[int],
) -> dict[str, Any]:
    updated: list[dict[str, Any]] = []
    for eid in entity_ids:
        updated.append(
            upsert_review(
                engine,
                case_id,
                entity_id=eid,
                hidden=False,
                hidden_reason=None,
                force_clear_hidden=True,
            )
        )
    return {"updated": len(updated), "reviews": updated}


def set_inventory_approval(
    engine: Engine,
    case_id: int,
    entity_id: int,
    *,
    approved: bool,
    inventory_priority: str | None = None,
    inventory_note: str | None = None,
    approved_reason: str | None = None,
) -> dict[str, Any]:
    if approved:
        out = approve_entities(
            engine,
            case_id,
            [entity_id],
            inventory_priority=inventory_priority,
            inventory_note=inventory_note,
            approved_reason=approved_reason,
        )
        return cast(dict[str, Any], out["reviews"][0])
    removed = remove_from_inventory(engine, case_id, [entity_id])
    return cast(dict[str, Any], removed["reviews"][0])


def bulk_review(
    engine: Engine,
    case_id: int,
    *,
    entity_ids: list[int] | None = None,
    evidence_ids: list[int] | None = None,
    values: list[str] | None = None,
    action: str | None = None,
    review_status: str | None = None,
    hidden: bool | None = None,
    hidden_reason: str | None = None,
    note: str | None = None,
    approved_for_inventory: bool | None = None,
    inventory_status: str | None = None,
    inventory_priority: str | None = None,
    inventory_note: str | None = None,
    approved_reason: str | None = None,
    clear_approval: bool = False,
) -> dict[str, Any]:
    """Bulk review; prefer ``action`` for unambiguous semantics."""
    ids = list(entity_ids or [])
    if action == "approve" or approved_for_inventory is True:
        return approve_entities(
            engine,
            case_id,
            ids,
            inventory_priority=inventory_priority,
            inventory_note=inventory_note,
            approved_reason=approved_reason,
        )
    if action == "remove_inventory" or clear_approval:
        return remove_from_inventory(engine, case_id, ids)
    if action == "discard" or review_status == "discarded" or hidden is True:
        return discard_entities(engine, case_id, ids, hidden_reason=hidden_reason, note=note)
    if action == "restore" or hidden is False:
        return restore_entities(engine, case_id, ids)

    updated: list[dict[str, Any]] = []
    for eid in ids:
        updated.append(
            upsert_review(
                engine,
                case_id,
                entity_id=eid,
                review_status=review_status,
                hidden=hidden,
                hidden_reason=hidden_reason,
                note=note,
                approved_for_inventory=approved_for_inventory,
                inventory_status=inventory_status,
                inventory_priority=inventory_priority,
                inventory_note=inventory_note,
                approved_reason=approved_reason,
                clear_approval=clear_approval,
            )
        )
    for evid in evidence_ids or []:
        with Session(engine) as session:
            ev = session.get(StoredEvidence, evid)
        updated.append(
            upsert_review(
                engine,
                case_id,
                evidence_id=evid,
                entity_id=int(ev.entity_id) if ev and ev.entity_id else None,
                value=ev.finding_value if ev else None,
                review_status=review_status,
                hidden=hidden,
                hidden_reason=hidden_reason,
                note=note,
                approved_for_inventory=approved_for_inventory,
                inventory_status=inventory_status,
                inventory_priority=inventory_priority,
                inventory_note=inventory_note,
                approved_reason=approved_reason,
                clear_approval=clear_approval,
            )
        )
    for val in values or []:
        updated.append(
            upsert_review(
                engine,
                case_id,
                value=val,
                review_status=review_status,
                hidden=hidden,
                hidden_reason=hidden_reason,
                note=note,
                approved_for_inventory=approved_for_inventory,
                inventory_status=inventory_status,
                inventory_priority=inventory_priority,
                inventory_note=inventory_note,
                approved_reason=approved_reason,
                clear_approval=clear_approval,
            )
        )
    return {"updated": len(updated), "reviews": updated}
