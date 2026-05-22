"""FastAPI integration tests (in-process ASGI, HTTP mocked)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from globeye.api.main import create_app
from globeye.config import Settings


@pytest.fixture
def api_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        api_key="TEST-KEY",
        cache_enabled=False,
        http_max_retries=0,
        db_url=f"sqlite:///{tmp_path}/history.db",
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


async def test_health_no_auth(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "crtsh" in body["sources"]


async def test_sources_catalogue(client):
    r = await client.get("/api/sources")
    assert r.status_code == 200
    data = r.json()
    by_name = {s["name"]: s for s in data}
    assert "crtsh" in by_name
    assert by_name["crtsh"]["label"] == "crt.sh"
    assert by_name["crtsh"]["requires_api_key"] is False
    assert by_name["crtsh"]["available"] is True
    # A keyed source with no key configured reports itself unavailable.
    assert by_name["shodan"]["requires_api_key"] is True
    assert by_name["shodan"]["available"] is False
    assert by_name["shodan"]["configured"] is False
    assert by_name["crtsh"]["configured"] is True


async def test_sources_status_no_secrets(client):
    r = await client.get("/api/sources/status")
    assert r.status_code == 200
    data = r.json()
    assert any(row["name"] == "crtsh" for row in data)
    crtsh = next(row for row in data if row["name"] == "crtsh")
    assert crtsh["status"] == "keyless"
    assert crtsh["configured"] is True
    assert "api_key" not in {k for row in data for k in row}
    assert all("shodan_api_key" not in str(row) for row in data)


async def test_sources_status_check_mocked(client, respx_mock, load_fixture):
    respx_mock.get("https://crt.sh/").mock(
        return_value=httpx.Response(200, json=load_fixture("crtsh_example_com.json"))
    )
    respx_mock.get("https://web.archive.org/cdx/search/cdx").mock(
        return_value=httpx.Response(200, json=[["urlkey"], ["http://example.com/"]])
    )
    respx_mock.get("https://rdap.org/domain/example.com").mock(
        return_value=httpx.Response(
            302,
            headers={"Location": "https://rdap.verisign.com/domain/example.com"},
        )
    )
    respx_mock.get("https://rdap.verisign.com/domain/example.com").mock(
        return_value=httpx.Response(200, json={"ldhName": "example.com", "entities": []})
    )
    r = await client.get("/api/sources/status", params={"check": "true"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 5
    crtsh = next(row for row in data if row["name"] == "crtsh")
    assert crtsh["status"] == "ok"
    rdap = next(row for row in data if row["name"] == "rdap")
    assert rdap["credential_status"] == "valid"


async def test_scan_requires_api_key(client):
    r = await client.post("/api/scan", json={"target": "example.com"})
    assert r.status_code == 401


async def test_scan_history_and_report(client, respx_mock, load_fixture):
    _mock_domain_sources(respx_mock, load_fixture)
    headers = {"X-API-Key": "TEST-KEY"}

    r = await client.post("/api/scan", json={"target": "example.com"}, headers=headers)
    assert r.status_code == 200, r.text
    payload = r.json()
    scan_id = payload["scan_id"]
    values = {f["value"] for f in payload["findings"]}
    assert "api.example.com" in values

    h = await client.get("/api/history", headers=headers)
    assert h.status_code == 200
    assert len(h.json()) == 1

    item = await client.get(f"/api/history/{scan_id}", headers=headers)
    assert item.status_code == 200
    assert item.json()["target"]["value"] == "example.com"

    rep = await client.get(f"/api/scan/{scan_id}/report", headers=headers)
    assert rep.status_code == 200
    assert "text/html" in rep.headers["content-type"]
    assert "example.com" in rep.text
    assert "GLOBEYE" in rep.text


async def test_scan_invalid_target(client):
    r = await client.post("/api/scan", json={"target": "   "}, headers={"X-API-Key": "TEST-KEY"})
    assert r.status_code == 422


async def test_history_item_not_found(client):
    r = await client.get("/api/history/999", headers={"X-API-Key": "TEST-KEY"})
    assert r.status_code == 404
