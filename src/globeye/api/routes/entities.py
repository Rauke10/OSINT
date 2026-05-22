"""Entity and relationship endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select
from starlette.concurrency import run_in_threadpool

from globeye.api.auth import get_engine, require_api_key
from globeye.api.deps import get_case_or_404
from globeye.api.schemas.cases import EntityOut, EntityRelationshipsOut, RelationshipEdge
from globeye.api.schemas.trace import EntityTraceOut
from globeye.db.models import Entity, EntityRelationship
from globeye.services.entity_trace import build_entity_trace
from globeye.services.finding_quality import quality_for_entity

router = APIRouter(tags=["entities"], dependencies=[Depends(require_api_key)])


def _entity_out(ent: Entity, *, quality: Any | None = None) -> EntityOut:
    base = EntityOut(
        id=int(ent.id or 0),
        case_id=ent.case_id,
        entity_type=ent.entity_type,
        normalized_value=ent.normalized_value,
        display_value=ent.display_value,
        first_seen_at=ent.first_seen_at,
        last_seen_at=ent.last_seen_at,
        last_job_id=ent.last_job_id,
    )
    if quality is None:
        return base
    return base.model_copy(
        update={
            "quality_label": quality.quality_label,
            "confidence_score": quality.confidence_score,
            "verification_sources_count": quality.verification_sources_count,
            "is_historical": quality.is_historical,
            "is_potential_false_positive": quality.is_potential_false_positive,
            "quality_reason": quality.quality_reason,
        }
    )


@router.get("/api/cases/{case_id}/entities")
async def list_case_entities(
    case_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
    entity_type: str | None = None,
    limit: int = 500,
) -> list[EntityOut]:
    await run_in_threadpool(get_case_or_404, engine, case_id)
    limit = min(max(limit, 1), 2000)

    def _list() -> list[EntityOut]:
        with Session(engine) as session:
            stmt = select(Entity).where(Entity.case_id == case_id)
            if entity_type:
                stmt = stmt.where(Entity.entity_type == entity_type)
            stmt = stmt.order_by(col(Entity.last_seen_at).desc()).limit(limit)
            rows = list(session.exec(stmt).all())
        out: list[EntityOut] = []
        for r in rows:
            q = quality_for_entity(
                engine,
                case_id,
                entity_type=r.entity_type,
                normalized_value=r.normalized_value,
            )
            out.append(_entity_out(r, quality=q))
        return out

    return await run_in_threadpool(_list)


@router.get("/api/entities/{entity_id}/relationships")
async def get_entity_relationships(
    entity_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
) -> EntityRelationshipsOut:
    def _get() -> EntityRelationshipsOut:
        with Session(engine) as session:
            entity = session.get(Entity, entity_id)
            if entity is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="entity not found"
                )

            outgoing_rows = list(
                session.exec(
                    select(EntityRelationship).where(
                        EntityRelationship.source_entity_id == entity_id
                    )
                ).all()
            )
            incoming_rows = list(
                session.exec(
                    select(EntityRelationship).where(
                        EntityRelationship.target_entity_id == entity_id
                    )
                ).all()
            )

            outgoing: list[RelationshipEdge] = []
            for rel in outgoing_rows:
                peer = session.get(Entity, rel.target_entity_id)
                if peer is None:
                    continue
                outgoing.append(
                    RelationshipEdge(
                        id=int(rel.id or 0),
                        relationship_type=rel.relationship_type,
                        source_name=rel.source_name,
                        peer_entity_id=int(peer.id or 0),
                        peer_entity_type=peer.entity_type,
                        peer_display_value=peer.display_value,
                        direction="outgoing",
                    )
                )

            incoming: list[RelationshipEdge] = []
            for rel in incoming_rows:
                peer = session.get(Entity, rel.source_entity_id)
                if peer is None:
                    continue
                incoming.append(
                    RelationshipEdge(
                        id=int(rel.id or 0),
                        relationship_type=rel.relationship_type,
                        source_name=rel.source_name,
                        peer_entity_id=int(peer.id or 0),
                        peer_entity_type=peer.entity_type,
                        peer_display_value=peer.display_value,
                        direction="incoming",
                    )
                )

        return EntityRelationshipsOut(
            entity_id=entity_id,
            outgoing=outgoing,
            incoming=incoming,
        )

    return await run_in_threadpool(_get)


@router.get("/api/entities/{entity_id}/trace", response_model=EntityTraceOut)
async def get_entity_trace(
    entity_id: int,
    engine: Annotated[Engine, Depends(get_engine)],
) -> dict[str, Any]:
    """Traceability: originals, normalization, grouping, evidence (Fase 2C.4)."""

    def _trace() -> dict[str, Any]:
        payload = build_entity_trace(engine, entity_id)
        if payload.get("error"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(payload["error"]),
            )
        with Session(engine) as session:
            ent = session.get(Entity, entity_id)
        if ent is not None:
            q = quality_for_entity(
                engine,
                int(ent.case_id),
                entity_type=ent.entity_type,
                normalized_value=ent.normalized_value,
            )
            payload["quality"] = {
                "label": q.quality_label,
                "reason": q.quality_reason,
            }
        return payload

    return await run_in_threadpool(_trace)
