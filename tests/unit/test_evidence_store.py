"""Evidence and source result persistence (Fase 2A)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlmodel import Session, select

from globeye.config import Settings
from globeye.core.models import (
    Confidence,
    Evidence,
    Finding,
    ScanResult,
    SourceRun,
    Target,
    TargetType,
)
from globeye.db.models import SourceResult, StoredEvidence
from globeye.services.evidence_store import persist_scan_traceability
from globeye.services.source_errors import skip_reason_to_status
from globeye.utils.redact import Redactor
from tests.support.settings_env import apply_test_env


def test_skip_reason_to_status_mapping():
    assert skip_reason_to_status("missing API key — configure in .env") == "missing_key"
    assert skip_reason_to_status("invalid API key") == "invalid_key"
    assert skip_reason_to_status("rate limited") == "rate_limited"


def test_persist_source_results_and_evidence(tmp_path, monkeypatch):
    shodan_placeholder = "SHODAN-UNIT-TEST-PLACEHOLDER"
    apply_test_env(monkeypatch, app_key="TEST-KEY", shodan=shodan_placeholder)
    settings = Settings(_env_file=None, db_url=f"sqlite:///{tmp_path}/ev.db")
    from globeye.core.db import make_engine

    engine = make_engine(settings.db_url)
    now = datetime.now(UTC)
    target = Target(raw="example.com", type=TargetType.DOMAIN, value="example.com")
    raw = {"credential": shodan_placeholder, "note": "ok"}
    finding = Finding(
        source="crtsh",
        target="example.com",
        confidence=Confidence.HIGH,
        kind="subdomain",
        value="api.example.com",
        raw_evidence=Evidence(source_url="https://crt.sh/", raw=raw),
    )
    result = ScanResult(
        target=target,
        started_at=now,
        finished_at=now,
        sources_used=["crtsh"],
        sources_skipped={"shodan": "missing API key — configure in .env"},
        findings=[finding],
        source_runs=[
            SourceRun(
                name="crtsh",
                status="used",
                findings_count=1,
                started_at=now,
                finished_at=now,
                latency_ms=120,
            )
        ],
    )

    sr_count, ev_count = persist_scan_traceability(
        engine, settings, case_id=1, job_id=10, result=result
    )
    assert sr_count == 2
    assert ev_count >= 1

    with Session(engine) as session:
        sources = list(session.exec(select(SourceResult)).all())
        evidence = list(session.exec(select(StoredEvidence)).all())

    assert len(sources) == 2
    shodan = next(s for s in sources if s.source_name == "shodan")
    assert shodan.status == "missing_key"

    assert len(evidence) >= 1
    row = evidence[0]
    assert row.content_hash_sha256
    assert len(row.content_hash_sha256) == 64
    assert row.redacted or shodan_placeholder not in (row.raw_json or "")
    redactor = Redactor(settings.secret_values())
    scrubbed = redactor.scrub(json.loads(row.raw_json or "{}"))
    assert shodan_placeholder not in json.dumps(scrubbed)


def test_evidence_without_entity_id(tmp_path):
    settings = Settings(_env_file=None, db_url=f"sqlite:///{tmp_path}/ev2.db")
    from globeye.core.db import make_engine

    engine = make_engine(settings.db_url)
    now = datetime.now(UTC)
    target = Target(raw="8.8.8.8", type=TargetType.IP, value="8.8.8.8")
    finding = Finding(
        source="rdap",
        target="8.8.8.8",
        confidence=Confidence.MEDIUM,
        kind="registration",
        value="8.8.8.8",
        raw_evidence=Evidence(source_url="https://rdap.org/", raw={"status": "ok"}),
    )
    result = ScanResult(
        target=target,
        started_at=now,
        finished_at=now,
        sources_used=["rdap"],
        findings=[finding],
        source_runs=[SourceRun(name="rdap", status="used", findings_count=1, latency_ms=50)],
    )
    persist_scan_traceability(engine, settings, case_id=2, job_id=20, result=result)
    with Session(engine) as session:
        row = session.exec(select(StoredEvidence)).first()
    assert row is not None
    assert row.entity_id is None
