"""Persist SourceResult and StoredEvidence for case-bound scans (Fase 2A)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from globeye.config import Settings
from globeye.core.models import Finding, ScanResult, SourceRun
from globeye.db.models import Entity, SourceResult, StoredEvidence
from globeye.services.source_errors import error_type_from_reason, skip_reason_to_status
from globeye.utils.redact import Redactor

_MAX_RAW_BYTES = 100_000
_SENSITIVE_KINDS = frozenset({"breach", "breach_record", "password", "credential"})
_SECRET_IN_JSON = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|authorization|bearer)\s*[:=]\s*['\"]?\S+"
)


def persist_scan_traceability(
    engine: Engine,
    settings: Settings,
    *,
    case_id: int,
    job_id: int,
    result: ScanResult,
) -> tuple[int, int]:
    """Write source results and evidence rows. Returns (source_results, evidence)."""
    redactor = Redactor(settings.secret_values())
    counts_by_source = _findings_per_source(result.findings)
    runs_by_name = _merge_source_runs(result, counts_by_source)

    with Session(engine) as session:
        sr_ids: dict[str, int] = {}
        for name, run in sorted(runs_by_name.items()):
            row = SourceResult(
                case_id=case_id,
                scan_job_id=job_id,
                source_name=name,
                status=run.status,
                findings_count=run.findings_count,
                started_at=run.started_at,
                finished_at=run.finished_at,
                latency_ms=run.latency_ms,
                message=run.message,
                error_type=run.error_type,
            )
            session.add(row)
            session.flush()
            sr_ids[name] = int(row.id or 0)

        evidence_count = 0
        for finding in result.findings:
            if not _should_persist_evidence(finding):
                continue
            sr_id = sr_ids.get(finding.source)
            entity_id = _lookup_entity_id(session, case_id, finding)
            ev_rows = _build_evidence_rows(
                case_id=case_id,
                job_id=job_id,
                source_result_id=sr_id,
                entity_id=entity_id,
                finding=finding,
                redactor=redactor,
            )
            for ev_row in ev_rows:
                session.add(ev_row)
                evidence_count += 1

        session.commit()

    return len(runs_by_name), evidence_count


def _findings_per_source(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.source] = counts.get(f.source, 0) + 1
    return counts


def _merge_source_runs(
    result: ScanResult,
    counts_by_source: dict[str, int],
) -> dict[str, SourceRun]:
    merged: dict[str, SourceRun] = {}
    for run in result.source_runs:
        merged[run.name] = run

    for name in result.sources_used:
        count = counts_by_source.get(name, 0)
        status = "no_results" if count == 0 else "used"
        if name in merged:
            merged[name].findings_count = count
            if merged[name].status == "used" and status == "no_results":
                merged[name].status = "no_results"
                merged[name].message = "Queried successfully, no findings"
        else:
            now = result.finished_at
            merged[name] = SourceRun(
                name=name,
                status=status,
                findings_count=count,
                started_at=result.started_at,
                finished_at=now,
                message=None if count else "Queried successfully, no findings",
            )

    for name, reason in result.sources_skipped.items():
        status = skip_reason_to_status(reason)
        merged[name] = SourceRun(
            name=name,
            status=status,
            findings_count=0,
            started_at=result.started_at,
            finished_at=result.finished_at,
            message=reason[:2000],
            error_type=error_type_from_reason(reason),
        )

    return merged


def _should_persist_evidence(finding: Finding) -> bool:
    if finding.kind in _SENSITIVE_KINDS:
        return False
    if finding.raw_evidence is not None:
        return finding.raw_evidence.raw is not None or bool(finding.raw_evidence.source_url)
    return False


def _lookup_entity_id(session: Session, case_id: int, finding: Finding) -> int | None:
    hint = finding.graph_node_hint
    if hint is not None:
        entity_type = hint.node_type
        lower_types = {"email", "domain", "subdomain", "username"}
        norm = hint.node_id.lower() if entity_type in lower_types else hint.node_id
    else:
        entity_type = finding.kind
        lower_types = {"email", "domain", "subdomain", "username"}
        norm = finding.value.lower() if entity_type in lower_types else finding.value
    stmt = select(Entity).where(
        Entity.case_id == case_id,
        Entity.entity_type == entity_type,
        Entity.normalized_value == norm,
    )
    row = session.exec(stmt).first()
    return int(row.id or 0) if row else None


def _build_evidence_rows(
    *,
    case_id: int,
    job_id: int,
    source_result_id: int | None,
    entity_id: int | None,
    finding: Finding,
    redactor: Redactor,
) -> list[StoredEvidence]:
    ev = finding.raw_evidence
    if ev is None:
        return []
    rows: list[StoredEvidence] = []
    collected = ev.retrieved_at
    sensitive = finding.kind in _SENSITIVE_KINDS or _looks_sensitive(finding.value)

    if ev.source_url:
        url = redactor.scrub(str(ev.source_url))
        rows.append(
            _evidence_row(
                case_id=case_id,
                job_id=job_id,
                source_result_id=source_result_id,
                entity_id=entity_id,
                finding=finding,
                evidence_type="url",
                source_url=url,
                raw_json=None,
                collected_at=collected,
                sensitive=sensitive,
                redacted=url != ev.source_url,
            )
        )

    if ev.raw is not None:
        payload = _prepare_raw_payload(ev.raw, redactor)
        if payload is not None:
            rows.append(
                _evidence_row(
                    case_id=case_id,
                    job_id=job_id,
                    source_result_id=source_result_id,
                    entity_id=entity_id,
                    finding=finding,
                    evidence_type="raw_json",
                    source_url=None,
                    raw_json=payload,
                    collected_at=collected,
                    sensitive=sensitive or bool(payload.get("_redacted")),
                    redacted=bool(payload.get("_redacted")),
                )
            )
    elif finding.normalized_data and not rows:
        meta = redactor.scrub(finding.normalized_data)
        rows.append(
            _evidence_row(
                case_id=case_id,
                job_id=job_id,
                source_result_id=source_result_id,
                entity_id=entity_id,
                finding=finding,
                evidence_type="metadata",
                source_url=None,
                raw_json=json.dumps(meta, sort_keys=True, default=str),
                collected_at=collected,
                sensitive=sensitive,
                redacted=False,
            )
        )

    return rows


def _prepare_raw_payload(raw: Any, redactor: Redactor) -> dict[str, Any] | None:
    scrubbed = redactor.scrub(raw)
    text = json.dumps(scrubbed, sort_keys=True, default=str)
    if len(text.encode()) > _MAX_RAW_BYTES:
        text = text[:_MAX_RAW_BYTES] + "…"
    redacted = text != json.dumps(raw, sort_keys=True, default=str)
    if _SECRET_IN_JSON.search(text):
        redacted = True
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            data = {"value": data}
    except json.JSONDecodeError:
        data = {"value": text}
    if redacted:
        data["_redacted"] = True
    return data


def _looks_sensitive(value: str) -> bool:
    lower = value.lower()
    return any(tok in lower for tok in ("password", "secret", "api_key", "token"))


def _evidence_row(
    *,
    case_id: int,
    job_id: int,
    source_result_id: int | None,
    entity_id: int | None,
    finding: Finding,
    evidence_type: str,
    source_url: str | None,
    raw_json: dict[str, Any] | str | None,
    collected_at: datetime,
    sensitive: bool,
    redacted: bool,
) -> StoredEvidence:
    raw_text: str | None
    if isinstance(raw_json, dict):
        raw_text = json.dumps(raw_json, sort_keys=True, default=str)
    else:
        raw_text = raw_json
    content = raw_text or source_url or f"{finding.kind}:{finding.value}"
    digest = hashlib.sha256(content.encode()).hexdigest()
    return StoredEvidence(
        case_id=case_id,
        scan_job_id=job_id,
        source_result_id=source_result_id,
        entity_id=entity_id,
        finding_kind=finding.kind,
        finding_value=finding.value[:512],
        source_name=finding.source,
        evidence_type=evidence_type,
        source_url=source_url,
        raw_json=raw_text,
        content_hash_sha256=digest,
        collected_at=collected_at,
        sensitive=sensitive,
        redacted=redacted,
    )
