"""HTML report, relationship graph and SQLite history (no network)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from globeye.core.db import get_scan, list_scans, make_engine, save_scan
from globeye.core.models import (
    Confidence,
    Finding,
    GraphNodeHint,
    ScanResult,
    Target,
    TargetType,
)
from globeye.report.graph import build_graph
from globeye.report.html_writer import to_html, write_html


def _result() -> ScanResult:
    t = Target(raw="example.com", type=TargetType.DOMAIN, value="example.com")
    now = datetime(2024, 1, 1, tzinfo=UTC)
    f = Finding(
        source="crtsh",
        target="example.com",
        confidence=Confidence.HIGH,
        kind="subdomain",
        value="api.example.com",
        graph_node_hint=GraphNodeHint(
            node_type="domain",
            node_id="api.example.com",
            label="api.example.com",
            parent_id="example.com",
        ),
    )
    plain = Finding(
        source="otx",
        target="example.com",
        confidence=Confidence.LOW,
        kind="passive_dns",
        value="mail.example.com",
    )
    return ScanResult(
        target=t,
        started_at=now,
        finished_at=now,
        sources_used=["crtsh", "otx"],
        findings=[f, plain],
    )


def test_build_graph():
    g = build_graph(_result())
    ids = {n["data"]["id"] for n in g["nodes"]}
    assert "example.com" in ids
    assert "api.example.com" in ids
    assert any(n["data"].get("root") for n in g["nodes"])
    assert any(e["data"]["via"] == "crtsh" for e in g["edges"])


def test_to_html_is_self_contained():
    html = to_html(_result())
    assert "<html" in html
    assert "GLOBEYE" in html
    assert "api.example.com" in html
    # Truly standalone: no external scripts / CDN dependencies.
    assert "<script src=" not in html
    assert "cdn." not in html


def test_write_html(tmp_path: Path):
    out = write_html(_result(), tmp_path / "r" / "report.html")
    assert out.exists()
    assert "example.com" in out.read_text(encoding="utf-8")


def test_html_report_scales_for_large_results():
    """A 1000-finding scan must stay small and embed the data only once."""
    t = Target(raw="big.example", type=TargetType.DOMAIN, value="big.example")
    now = datetime(2024, 1, 1, tzinfo=UTC)
    findings = [
        Finding(
            source="wayback",
            target="big.example",
            confidence=Confidence.LOW,
            kind="archived_url",
            value=f"https://big.example/path/{i}",
        )
        for i in range(1000)
    ]
    html = to_html(
        ScanResult(
            target=t,
            started_at=now,
            finished_at=now,
            sources_used=["wayback"],
            findings=findings,
        )
    )
    # Findings embedded exactly once (no server-side timeline/graph dup).
    assert html.count('id="data"') == 1
    assert html.count("https://big.example/path/999") == 1
    # Old triplicated template was ~840 KB for ~1000 findings; this stays lean.
    assert len(html.encode()) < 300_000


def test_report_documents_sources_used_and_skipped():
    """The report must make the OSINT tooling provenance explicit."""
    t = Target(raw="example.com", type=TargetType.DOMAIN, value="example.com")
    now = datetime(2024, 1, 1, tzinfo=UTC)
    res = ScanResult(
        target=t,
        started_at=now,
        finished_at=now,
        sources_used=["crtsh"],
        sources_skipped={"shodan": "missing API key", "rdap": "error: timeout"},
        findings=[
            Finding(
                source="crtsh",
                target="example.com",
                confidence=Confidence.HIGH,
                kind="subdomain",
                value="api.example.com",
            )
        ],
    )
    html = to_html(res)
    assert "Sources consulted" in html
    # Human-friendly tool names + descriptions are present.
    assert "crt.sh" in html
    assert "Certificate Transparency" in html
    assert "Have I Been Pwned" in html or "Shodan" in html
    # Skip reasons are carried through so the report is unambiguous.
    assert "missing API key" in html
    assert "error: timeout" in html
    # Provenance data embedded for client-side rendering.
    assert 'id="sourcesdata"' in html


def test_db_roundtrip(tmp_path: Path):
    engine = make_engine(f"sqlite:///{tmp_path}/h.db")
    sid = save_scan(engine, _result())
    assert sid >= 1
    rows = list_scans(engine)
    assert len(rows) == 1
    assert rows[0].target_value == "example.com"
    rec = get_scan(engine, sid)
    assert rec is not None
    restored = ScanResult.model_validate_json(rec.model_json)
    assert restored.target.value == "example.com"
    assert len(restored.findings) == 2
    assert get_scan(engine, 999) is None
