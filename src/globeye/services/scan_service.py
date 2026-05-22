"""Case-bound and legacy scan orchestration with persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from globeye.config import Settings
from globeye.core.db import save_scan
from globeye.core.models import ScanResult, SourceRun, Target
from globeye.core.orchestrator import Orchestrator
from globeye.core.source_profiles import ScanDepth
from globeye.db.models import ScanJob
from globeye.report.json_writer import to_dict
from globeye.services.entity_normalizer import persist_entities_from_scan
from globeye.services.evidence_store import persist_scan_traceability
from globeye.services.finding_quality import annotate_scan_result
from globeye.services.source_router import effective_pivot, plan_routing


async def run_legacy_scan(
    engine: Engine,
    settings: Settings,
    target: Target,
    *,
    pivot: bool = False,
) -> dict[str, Any]:
    """Run a scan without a case (``POST /api/scan`` contract)."""
    result = await Orchestrator(settings).scan(target, pivot=pivot)
    scan_id = save_scan(engine, result)
    payload = to_dict(result)
    payload["scan_id"] = scan_id
    return payload


def _apply_routing(
    result: ScanResult,
    *,
    plan_preview: dict[str, object],
    skipped_missing_key: list[str],
) -> ScanResult:
    """Attach routing metadata and synthetic runs for profile-skipped keys."""
    now = result.finished_at
    existing = {r.name for r in result.source_runs}
    runs = list(result.source_runs)
    for name in skipped_missing_key:
        if name in existing:
            continue
        runs.append(
            SourceRun(
                name=name,
                status="missing_key",
                message="API key missing or not configured in .env",
                started_at=now,
                finished_at=now,
                latency_ms=0,
                error_type="missing_key",
            )
        )
        result.sources_skipped.setdefault(name, "missing API key — configure in .env")
    result.source_runs = runs
    result.routing = plan_preview
    return result


async def run_case_scan(
    engine: Engine,
    settings: Settings,
    *,
    case_id: int,
    target: Target,
    pivot: bool = False,
    depth: ScanDepth | str = ScanDepth.STANDARD,
    selected_sources: list[str] | None = None,
) -> dict[str, Any]:
    """Run a scan within a case: job + ScanRecord + entities."""
    now = datetime.now(UTC)
    job = ScanJob(
        case_id=case_id,
        target_raw=target.raw,
        target_type=target.type.value,
        target_value=target.value,
        pivot=pivot,
        status="pending",
        started_at=now,
    )
    with Session(engine) as session:
        session.add(job)
        session.commit()
        session.refresh(job)
    job_id = int(job.id or 0)

    try:
        _update_job(engine, job_id, status="running")
        plan = plan_routing(settings, target, depth=depth, selected_sources=selected_sources)
        use_pivot, max_pivot = effective_pivot(depth, pivot)
        result = await Orchestrator(settings).scan(
            target,
            pivot=use_pivot,
            max_pivot_depth=max_pivot,
            source_names=plan.source_names_to_run,
        )
        skipped_names = [e.source for e in plan.skipped_missing_key]
        result = _apply_routing(
            result,
            plan_preview=plan.to_preview_dict(),
            skipped_missing_key=skipped_names,
        )
        annotate_scan_result(result)
        scan_id = save_scan(engine, result)
        persist_entities_from_scan(engine, case_id=case_id, job_id=job_id, result=result)
        persist_scan_traceability(engine, settings, case_id=case_id, job_id=job_id, result=result)
        _update_job(
            engine,
            job_id,
            status="completed",
            scan_record_id=scan_id,
            findings_count=len(result.findings),
            finished_at=datetime.now(UTC),
        )
    except Exception as exc:
        _update_job(
            engine,
            job_id,
            status="failed",
            error_message=f"{type(exc).__name__}: {exc}"[:2000],
            finished_at=datetime.now(UTC),
        )
        raise

    payload = to_dict(result)
    payload["scan_id"] = scan_id
    payload["job_id"] = job_id
    payload["case_id"] = case_id
    return payload


def _update_job(
    engine: Engine,
    job_id: int,
    *,
    status: str,
    scan_record_id: int | None = None,
    findings_count: int | None = None,
    error_message: str | None = None,
    finished_at: datetime | None = None,
) -> None:
    with Session(engine) as session:
        job = session.get(ScanJob, job_id)
        if job is None:
            return
        job.status = status
        if scan_record_id is not None:
            job.scan_record_id = scan_record_id
        if findings_count is not None:
            job.findings_count = findings_count
        if error_message is not None:
            job.error_message = error_message
        if finished_at is not None:
            job.finished_at = finished_at
        session.add(job)
        session.commit()


async def run_cli_case_scan(
    engine: Engine,
    settings: Settings,
    *,
    case_id: int,
    target: Target,
    pivot: bool = False,
    depth: ScanDepth | str = ScanDepth.STANDARD,
    selected_sources: list[str] | None = None,
) -> ScanResult:
    """CLI helper: run case scan and return the scan result."""
    now = datetime.now(UTC)
    job = ScanJob(
        case_id=case_id,
        target_raw=target.raw,
        target_type=target.type.value,
        target_value=target.value,
        pivot=pivot,
        status="running",
        started_at=now,
    )
    with Session(engine) as session:
        session.add(job)
        session.commit()
        session.refresh(job)
    job_id = int(job.id or 0)

    try:
        plan = plan_routing(settings, target, depth=depth, selected_sources=selected_sources)
        use_pivot, max_pivot = effective_pivot(depth, pivot)
        result = await Orchestrator(settings).scan(
            target,
            pivot=use_pivot,
            max_pivot_depth=max_pivot,
            source_names=plan.source_names_to_run,
        )
        result = _apply_routing(
            result,
            plan_preview=plan.to_preview_dict(),
            skipped_missing_key=[e.source for e in plan.skipped_missing_key],
        )
        annotate_scan_result(result)
        scan_id = save_scan(engine, result)
        persist_entities_from_scan(engine, case_id=case_id, job_id=job_id, result=result)
        persist_scan_traceability(engine, settings, case_id=case_id, job_id=job_id, result=result)
        _update_job(
            engine,
            job_id,
            status="completed",
            scan_record_id=scan_id,
            findings_count=len(result.findings),
            finished_at=datetime.now(UTC),
        )
        return result
    except Exception as exc:
        _update_job(
            engine,
            job_id,
            status="failed",
            error_message=f"{type(exc).__name__}: {exc}"[:2000],
            finished_at=datetime.now(UTC),
        )
        raise
