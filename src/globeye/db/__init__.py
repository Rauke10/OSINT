"""SQLModel persistence for investigations (cases, jobs, entities)."""

from __future__ import annotations


def register_models() -> None:
    """Import all table models so :func:`SQLModel.metadata.create_all` sees them."""
    from globeye.db.models import case as _case
    from globeye.db.models import entity as _entity
    from globeye.db.models import entity_review as _entity_review
    from globeye.db.models import evidence as _evidence
    from globeye.db.models import job as _job
    from globeye.db.models import source_result as _source_result
    from globeye.db.models import url_live_check as _url_live_check

    _ = (_case, _entity, _evidence, _job, _source_result, _url_live_check, _entity_review)
