"""Live check for domain/subdomain entities."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from sqlmodel import Session, select

from globeye.config import Settings
from globeye.core.db import make_engine
from globeye.db.models import Case, Entity
from globeye.services.url_live_check import (
    MAX_BATCH_URLS,
    normalize_check_url,
    probe_url,
    run_url_checks,
    url_for_entity_check,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, cache_enabled=False, http_max_retries=0)


@pytest.mark.asyncio
async def test_domain_resolves_to_https(settings):
    url = url_for_entity_check("domain", "example.com", "example.com")
    assert url == "https://example.com"
    assert normalize_check_url(url) == "https://example.com"


@pytest.mark.asyncio
async def test_probe_domain_mock(respx_mock, settings):
    respx_mock.head("https://example.org/").mock(
        return_value=httpx.Response(200, headers={"content-type": "text/html"})
    )
    result = await probe_url("example.org", settings, method="HEAD", fallback_http=False)
    assert result["status"] == "live_200"


@pytest.mark.asyncio
async def test_fallback_http_on_network(respx_mock, settings):
    respx_mock.head("https://fail.test/").mock(return_value=httpx.Response(503, headers={}))
    respx_mock.head("http://fail.test/").mock(return_value=httpx.Response(200))
    result = await probe_url("https://fail.test", settings, method="HEAD", fallback_http=True)
    assert result["status"] in {"live_200", "server_error"}


def test_batch_limit_25():
    assert MAX_BATCH_URLS == 25


def test_run_checks_domain_entity(respx_mock, settings, tmp_path: Path):
    engine = make_engine(f"sqlite:///{tmp_path}/dom.db")
    respx_mock.head("https://corp.test/").mock(return_value=httpx.Response(403))
    with Session(engine) as session:
        session.add(Case(id=1, title="C", status="open"))
        session.add(
            Entity(
                case_id=1,
                entity_type="domain",
                normalized_value="corp.test",
                display_value="corp.test",
            )
        )
        session.commit()
        ent = session.exec(select(Entity).where(Entity.case_id == 1)).first()
    assert ent is not None
    assert ent.id is not None
    import asyncio

    out = asyncio.run(
        run_url_checks(
            engine,
            settings,
            1,
            [{"entity_id": int(ent.id), "url": ""}],
            max_urls=1,
        )
    )
    assert out["checked"] == 1
    assert out["results"][0]["status"] == "forbidden"
