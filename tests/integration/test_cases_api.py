"""Integration tests for case-based investigation API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from globeye.api.main import create_app
from globeye.config import Settings
from tests.support.settings_env import apply_test_env


@pytest.fixture
def api_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    apply_test_env(monkeypatch, app_key="TEST-KEY")
    return Settings(
        _env_file=None,
        cache_enabled=False,
        http_max_retries=0,
        db_url=f"sqlite:///{tmp_path}/cases.db",
    )


@pytest.fixture
async def client(api_settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(api_settings)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _mock_domain_sources(respx_mock: Any, load_fixture: Any) -> None:
    respx_mock.route(host="test").pass_through()
    respx_mock.get("https://crt.sh/").mock(
        return_value=httpx.Response(200, json=load_fixture("crtsh_example_com.json"))
    )
    for url in (
        "https://rdap.org/domain/example.com",
        "https://otx.alienvault.com/api/v1/indicators/domain/example.com/passive_dns",
        "https://web.archive.org/cdx/search/cdx",
    ):
        respx_mock.get(url).mock(return_value=httpx.Response(200, json={}))


@pytest.fixture
def headers() -> dict[str, str]:
    return {"X-API-Key": "TEST-KEY"}


async def test_case_crud(client, headers):
    r = await client.post(
        "/api/cases",
        json={"title": "ACME Investigation", "description": "test"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    case = r.json()
    case_id = case["id"]
    assert case["title"] == "ACME Investigation"
    assert case["status"] == "open"

    r = await client.get("/api/cases", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1

    r = await client.get(f"/api/cases/{case_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == case_id

    r = await client.patch(
        f"/api/cases/{case_id}",
        json={"status": "archived"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "archived"


async def test_case_target_duplicate_409(client, headers):
    r = await client.post("/api/cases", json={"title": "Dup"}, headers=headers)
    case_id = r.json()["id"]

    r1 = await client.post(
        f"/api/cases/{case_id}/targets",
        json={"target": "example.com"},
        headers=headers,
    )
    assert r1.status_code == 201

    r2 = await client.post(
        f"/api/cases/{case_id}/targets",
        json={"target": "example.com"},
        headers=headers,
    )
    assert r2.status_code == 409


async def test_case_scan_entities_jobs_graph(client, respx_mock, load_fixture, headers):
    _mock_domain_sources(respx_mock, load_fixture)

    r = await client.post("/api/cases", json={"title": "Scan case"}, headers=headers)
    case_id = r.json()["id"]

    r = await client.post(
        f"/api/cases/{case_id}/scans",
        json={"target": "example.com", "pivot": False},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["case_id"] == case_id
    assert "job_id" in payload
    assert "scan_id" in payload
    values = {f["value"] for f in payload["findings"]}
    assert "api.example.com" in values

    jobs = await client.get(f"/api/cases/{case_id}/jobs", headers=headers)
    assert jobs.status_code == 200
    assert len(jobs.json()) == 1
    assert jobs.json()[0]["status"] == "completed"

    job_id = payload["job_id"]
    job = await client.get(f"/api/jobs/{job_id}", headers=headers)
    assert job.status_code == 200
    assert job.json()["scan_record_id"] == payload["scan_id"]

    entities = await client.get(f"/api/cases/{case_id}/entities", headers=headers)
    assert entities.status_code == 200
    assert len(entities.json()) >= 2

    graph = await client.get(f"/api/cases/{case_id}/graph?mode=all", headers=headers)
    assert graph.status_code == 200
    g = graph.json()
    assert len(g["nodes"]) >= 2
    assert len(g["edges"]) >= 1

    graph_inv = await client.get(f"/api/cases/{case_id}/graph", headers=headers)
    assert graph_inv.status_code == 200
    assert len(graph_inv.json()["nodes"]) == 0

    ent_id = entities.json()[0]["id"]
    rels = await client.get(f"/api/entities/{ent_id}/relationships", headers=headers)
    assert rels.status_code == 200
    assert "outgoing" in rels.json()
    assert "incoming" in rels.json()

    sources = await client.get(f"/api/cases/{case_id}/sources", headers=headers)
    assert sources.status_code == 200
    src_rows = sources.json()
    assert len(src_rows) >= 1
    assert any(s["source_name"] == "crtsh" for s in src_rows)
    assert "api_key" not in str(src_rows).lower() or "missing_key" in str(src_rows)

    job_sources = await client.get(f"/api/jobs/{job_id}/sources", headers=headers)
    assert job_sources.status_code == 200
    assert len(job_sources.json()) >= 1

    evidence = await client.get(f"/api/cases/{case_id}/evidence", headers=headers)
    assert evidence.status_code == 200
    ev_list = evidence.json()
    if ev_list:
        ev_id = ev_list[0]["id"]
        detail = await client.get(f"/api/evidence/{ev_id}", headers=headers)
        assert detail.status_code == 200
        assert "content_hash_sha256" in detail.json()
        hash_r = await client.get(f"/api/evidence/{ev_id}/hash", headers=headers)
        assert hash_r.status_code == 200
        assert hash_r.json()["algorithm"] == "sha256"


async def test_legacy_scan_without_case(client, respx_mock, load_fixture, headers):
    _mock_domain_sources(respx_mock, load_fixture)

    r = await client.post(
        "/api/scan",
        json={"target": "example.com"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert "scan_id" in payload
    assert "case_id" not in payload
    assert "job_id" not in payload

    jobs = await client.get("/api/cases/1/jobs", headers=headers)
    assert jobs.status_code == 404


async def test_case_not_found(client, headers):
    r = await client.get("/api/cases/999", headers=headers)
    assert r.status_code == 404


async def test_source_routing_preview_ip(client, headers):
    r = await client.post(
        "/api/source-routing/preview",
        json={"target": "8.8.8.8", "depth": "standard"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["target_type"] == "ip"
    assert body["normalized_value"] == "8.8.8.8"
    assert body["profile"] == "ip_reputation_infrastructure"
    will = {x["source"] for x in body["will_run"]}
    skipped = {x["source"] for x in body["skipped_missing_key"]}
    assert "crtsh" not in will
    assert "crtsh" not in skipped
    na = {x["source"] for x in body["not_applicable"]}
    assert "crtsh" in na or "hunter" in na


async def test_source_routing_preview_domain(client, headers):
    r = await client.post(
        "/api/source-routing/preview",
        json={"target": "example.com", "depth": "quick"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["target_type"] == "domain"
    will = {x["source"] for x in body["will_run"]}
    assert "rdap" in will
    assert "crtsh" in will
    assert "shodan" not in will


def _mock_ip_sources(respx_mock: Any) -> None:
    respx_mock.route(host="test").pass_through()
    respx_mock.get("https://rdap.org/ip/8.8.8.8").mock(
        return_value=httpx.Response(200, json={"handle": "GOOGLE", "entities": []})
    )


async def test_case_data_endpoint(client, respx_mock, load_fixture, headers):
    _mock_domain_sources(respx_mock, load_fixture)

    r = await client.post("/api/cases", json={"title": "Data explorer"}, headers=headers)
    case_id = r.json()["id"]
    await client.post(
        f"/api/cases/{case_id}/scans",
        json={"target": "example.com", "depth": "quick"},
        headers=headers,
    )

    r = await client.get(f"/api/cases/{case_id}/data", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "summary" in body
    assert "items" in body
    assert body["summary"]["total_items"] >= 1
    assert body["total_count"] == body["counts"]["total_count"]
    assert body["visible_count"] == len(body["items"])
    assert "evidence_total_count" in body["counts"]

    r2 = await client.get(
        f"/api/cases/{case_id}/data",
        params={"type": "subdomain", "hide_noisy": "false"},
        headers=headers,
    )
    assert r2.status_code == 200
    if r2.json()["items"]:
        assert all(x["type"] == "subdomain" for x in r2.json()["items"])


async def test_case_quality_summary(client, respx_mock, load_fixture, headers):
    _mock_domain_sources(respx_mock, load_fixture)

    r = await client.post("/api/cases", json={"title": "Quality"}, headers=headers)
    case_id = r.json()["id"]
    await client.post(
        f"/api/cases/{case_id}/scans",
        json={"target": "example.com", "depth": "quick"},
        headers=headers,
    )

    r = await client.get(f"/api/cases/{case_id}/quality-summary", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["case_id"] == case_id
    assert "findings_by_label" in body
    assert body["total_findings"] >= 1


async def test_case_scan_ip_routing_sources(client, respx_mock, headers):
    _mock_ip_sources(respx_mock)

    r = await client.post("/api/cases", json={"title": "IP routing"}, headers=headers)
    case_id = r.json()["id"]

    r = await client.post(
        f"/api/cases/{case_id}/scans",
        json={"target": "8.8.8.8", "depth": "quick"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload.get("routing") is not None
    assert payload["routing"]["target_type"] == "ip"

    sources = await client.get(f"/api/cases/{case_id}/sources", headers=headers)
    names = {row["source_name"] for row in sources.json()}
    assert "crtsh" not in names
    assert "rdap" in names or "otx" in names


async def test_url_checks_api(client, respx_mock, load_fixture, headers):
    _mock_domain_sources(respx_mock, load_fixture)

    r = await client.post("/api/cases", json={"title": "URL live"}, headers=headers)
    case_id = r.json()["id"]
    await client.post(
        f"/api/cases/{case_id}/scans",
        json={"target": "example.com", "depth": "quick"},
        headers=headers,
    )

    target_url = "https://example.com/legacy-page"
    respx_mock.head(target_url).mock(return_value=httpx.Response(200))

    r = await client.post(
        f"/api/cases/{case_id}/url-checks",
        json={
            "urls": [target_url],
            "method": "HEAD",
            "fallback_get": True,
            "max_urls": 25,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    batch = r.json()
    assert batch["checked"] == 1
    result = batch["results"][0]
    assert result["status"] == "live_200"
    check_id = result["id"]

    r = await client.get(f"/api/cases/{case_id}/url-checks", headers=headers)
    assert r.status_code == 200
    assert any(row["id"] == check_id for row in r.json())

    r = await client.get(f"/api/url-checks/{check_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["url"] == target_url

    r = await client.get(
        f"/api/cases/{case_id}/url-checks",
        params={"status": "live_200"},
        headers=headers,
    )
    assert r.status_code == 200
    assert all(row["status"] == "live_200" for row in r.json())


async def test_url_checks_with_entity_id(client, respx_mock, load_fixture, headers):
    _mock_domain_sources(respx_mock, load_fixture)

    r = await client.post("/api/cases", json={"title": "URL entity"}, headers=headers)
    case_id = r.json()["id"]
    await client.post(
        f"/api/cases/{case_id}/scans",
        json={"target": "example.com", "depth": "quick"},
        headers=headers,
    )

    data = await client.get(f"/api/cases/{case_id}/data", headers=headers)
    url_items = [
        x
        for x in data.json()["items"]
        if x.get("is_wayback_url") or "wayback" in x.get("sources", [])
    ]
    if not url_items:
        pytest.skip("No Wayback URL entities in fixture data")

    row = url_items[0]
    check_url = row["display_value"] if row["display_value"].startswith("http") else row["value"]
    respx_mock.head(check_url).mock(return_value=httpx.Response(404))

    r = await client.post(
        f"/api/cases/{case_id}/url-checks",
        json={
            "entries": [
                {"url": check_url, "entity_id": row["id"], "evidence_id": None},
            ],
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["results"][0]["entity_id"] == row["id"]
    assert r.json()["results"][0]["status"] == "not_found"
