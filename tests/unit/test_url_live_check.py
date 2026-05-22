"""Unit tests for manual URL live checks (Fase 2C.2)."""

from __future__ import annotations

import httpx
import pytest

from globeye.config import Settings
from globeye.core.db import make_engine
from globeye.services.url_live_check import (
    MAX_BATCH_URLS,
    normalize_check_url,
    probe_url,
    redact_url_for_storage,
    run_url_checks,
    status_from_response,
)


def test_normalize_check_url_invalid():
    assert normalize_check_url("") is None
    assert normalize_check_url("ftp://evil.com/x") is None


def test_normalize_check_url_adds_scheme():
    assert normalize_check_url("example.com/path") == "https://example.com/path"


def test_status_from_response_mapping():
    assert status_from_response(200) == "live_200"
    assert status_from_response(301) == "redirect"
    assert status_from_response(403) == "forbidden"
    assert status_from_response(404) == "not_found"
    assert status_from_response(500) == "server_error"


def test_redact_secrets_in_url():
    settings = Settings(_env_file=None, shodan_api_key="SECRET-KEY-12345")
    url = "https://example.com/x?api_key=SECRET-KEY-12345&token=abc"
    out = redact_url_for_storage(url, settings)
    assert "SECRET-KEY-12345" not in out


@pytest.mark.asyncio
async def test_probe_invalid_url():
    settings = Settings(_env_file=None, cache_enabled=False)
    result = await probe_url("ftp://files.example.com/x", settings)
    assert result["status"] == "invalid_url"


@pytest.mark.asyncio
async def test_probe_head_200(respx_mock):
    settings = Settings(_env_file=None, cache_enabled=False, http_max_retries=0)
    respx_mock.head("https://example.com/old").mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "text/html", "Content-Length": "123"},
        )
    )
    result = await probe_url("https://example.com/old", settings, method="HEAD")
    assert result["status"] == "live_200"
    assert result["status_code"] == 200
    assert result["content_length"] == 123


@pytest.mark.asyncio
async def test_probe_head_redirect(respx_mock):
    settings = Settings(_env_file=None, cache_enabled=False)
    respx_mock.head("https://example.com/old").mock(
        return_value=httpx.Response(302, headers={"Location": "https://example.com/new"})
    )
    result = await probe_url("https://example.com/old", settings)
    assert result["status"] == "redirect"
    assert result["status_code"] == 302


@pytest.mark.asyncio
async def test_probe_head_403(respx_mock):
    settings = Settings(_env_file=None, cache_enabled=False)
    respx_mock.head("https://example.com/old").mock(return_value=httpx.Response(403))
    result = await probe_url("https://example.com/old", settings)
    assert result["status"] == "forbidden"


@pytest.mark.asyncio
async def test_probe_head_404(respx_mock):
    settings = Settings(_env_file=None, cache_enabled=False)
    respx_mock.head("https://example.com/old").mock(return_value=httpx.Response(404))
    result = await probe_url("https://example.com/old", settings)
    assert result["status"] == "not_found"


@pytest.mark.asyncio
async def test_probe_head_500(respx_mock):
    settings = Settings(_env_file=None, cache_enabled=False)
    respx_mock.head("https://example.com/old").mock(return_value=httpx.Response(500))
    result = await probe_url("https://example.com/old", settings)
    assert result["status"] == "server_error"


@pytest.mark.asyncio
async def test_probe_timeout(respx_mock):
    settings = Settings(_env_file=None, cache_enabled=False)
    respx_mock.head("https://example.com/old").mock(side_effect=httpx.ReadTimeout("timeout"))
    result = await probe_url("https://example.com/old", settings)
    assert result["status"] == "timeout"


@pytest.mark.asyncio
async def test_probe_head_405_fallback_get(respx_mock):
    settings = Settings(_env_file=None, cache_enabled=False)
    respx_mock.head("https://example.com/old").mock(return_value=httpx.Response(405))
    respx_mock.get("https://example.com/old").mock(return_value=httpx.Response(200))
    result = await probe_url("https://example.com/old", settings, method="HEAD", fallback_get=True)
    assert result["status"] == "live_200"
    assert result["method"] == "GET"


@pytest.mark.asyncio
async def test_run_url_checks_max_urls(tmp_path, respx_mock):
    from sqlmodel import Session

    from globeye.db.models import Case

    settings = Settings(
        _env_file=None,
        cache_enabled=False,
        db_url=f"sqlite:///{tmp_path}/live.db",
    )
    engine = make_engine(settings.db_url)
    with Session(engine) as session:
        case = Case(title="Live check test")
        session.add(case)
        session.commit()
        session.refresh(case)
        case_id = int(case.id or 0)
    for i in range(30):
        respx_mock.head(f"https://example.com/p{i}").mock(return_value=httpx.Response(404))
    urls = [f"https://example.com/p{i}" for i in range(30)]
    entries = [{"url": u} for u in urls]
    out = await run_url_checks(
        engine,
        settings,
        case_id,
        entries,
        max_urls=MAX_BATCH_URLS,
    )
    assert out["checked"] == MAX_BATCH_URLS
