"""Models + JSON report writer."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from globeye.core.models import (
    Confidence,
    Finding,
    RateLimit,
    ScanResult,
    Target,
    TargetType,
)
from globeye.report.json_writer import to_json, write_json


def _result() -> ScanResult:
    t = Target(raw="example.com", type=TargetType.DOMAIN, value="example.com")
    now = datetime(2024, 1, 1, tzinfo=UTC)
    findings = [
        Finding(
            source="crtsh",
            target="example.com",
            confidence=Confidence.HIGH,
            kind="subdomain",
            value="api.example.com",
        ),
        Finding(
            source="crtsh",
            target="example.com",
            confidence=Confidence.LOW,
            kind="subdomain",
            value="dev.example.com",
        ),
    ]
    return ScanResult(
        target=t,
        started_at=now,
        finished_at=now,
        sources_used=["crtsh"],
        findings=findings,
    )


def test_rate_limit_min_interval():
    assert RateLimit(rate=2, per=1).min_interval == 0.5
    assert RateLimit(rate=0, per=1).min_interval == 0.0


def test_scan_result_summary():
    r = _result()
    s = r.summary()
    assert s == {"low": 1, "medium": 0, "high": 1, "total": 2}
    assert r.duration_seconds == 0.0


def test_finding_dedup_key():
    f = Finding(source="s", target="t", confidence=Confidence.LOW, kind="k", value="V")
    assert f.dedup_key() == ("k", "v", "s")


def test_json_writer(tmp_path):
    r = _result()
    payload = json.loads(to_json(r))
    assert payload["summary"]["findings"]["total"] == 2
    assert payload["target"]["value"] == "example.com"

    out = write_json(r, tmp_path / "sub" / "report.json")
    assert out.exists()
    assert json.loads(out.read_text())["findings"][0]["source"] == "crtsh"
