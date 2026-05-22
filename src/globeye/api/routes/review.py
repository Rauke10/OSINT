"""Entity review and bulk discard (Fase 2C.3 / 2D)."""

from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import Engine
from sqlmodel import Session
from starlette.concurrency import run_in_threadpool

from globeye.api.auth import get_engine, require_api_key
from globeye.api.deps import get_case_or_404
from globeye.api.schemas.review import (
    BulkReviewIn,
    BulkReviewOut,
    EntityReviewOut,
    EntityReviewPatchIn,
)
from globeye.db.models import Entity
from globeye.services.entity_review import (
    approve_entities,
    bulk_review,
    discard_entities,
    remove_from_inventory,
    restore_entities,
    upsert_review,
)

router = APIRouter(tags=["review"], dependencies=[Depends(require_api_key)])


@router.patch("/api/entities/{entity_id}/review", response_model=EntityReviewOut)
async def patch_entity_review(
    entity_id: int,
    body: EntityReviewPatchIn,
    engine: Annotated[Engine, Depends(get_engine)],
) -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        with Session(engine) as session:
            ent = session.get(Entity, entity_id)
        if ent is None:
            raise HTTPException(status_code=404, detail="entity not found")
        if body.approved_for_inventory is True:
            approved = approve_entities(
                engine,
                ent.case_id,
                [entity_id],
                inventory_priority=body.inventory_priority,
                inventory_note=body.inventory_note,
                approved_reason=body.approved_reason,
            )
            return cast(dict[str, Any], approved["reviews"][0])
        if body.clear_approval:
            removed = remove_from_inventory(engine, ent.case_id, [entity_id])
            return cast(dict[str, Any], removed["reviews"][0])
        if body.review_status == "discarded" or body.hidden is True:
            discarded = discard_entities(
                engine,
                ent.case_id,
                [entity_id],
                hidden_reason=body.hidden_reason,
                note=body.note,
            )
            return cast(dict[str, Any], discarded["reviews"][0])
        if body.hidden is False:
            restored = restore_entities(engine, ent.case_id, [entity_id])
            return cast(dict[str, Any], restored["reviews"][0])
        return upsert_review(
            engine,
            ent.case_id,
            entity_id=entity_id,
            review_status=body.review_status,
            hidden=body.hidden,
            hidden_reason=body.hidden_reason,
            note=body.note,
            inventory_priority=body.inventory_priority,
            inventory_note=body.inventory_note,
            approved_reason=body.approved_reason,
        )

    return await run_in_threadpool(_run)


@router.post("/api/cases/{case_id}/data/bulk-review", response_model=BulkReviewOut)
async def bulk_case_review(
    case_id: int,
    body: BulkReviewIn,
    engine: Annotated[Engine, Depends(get_engine)],
) -> dict[str, Any]:
    await run_in_threadpool(get_case_or_404, engine, case_id)
    return await run_in_threadpool(
        bulk_review,
        engine,
        case_id,
        entity_ids=body.entity_ids,
        evidence_ids=body.evidence_ids,
        values=body.values,
        action=body.action,
        review_status=body.review_status,
        hidden=body.hidden,
        hidden_reason=body.hidden_reason,
        note=body.note,
        approved_for_inventory=body.approved_for_inventory,
        inventory_status=body.inventory_status,
        inventory_priority=body.inventory_priority,
        inventory_note=body.inventory_note,
        approved_reason=body.approved_reason,
        clear_approval=body.clear_approval,
    )
