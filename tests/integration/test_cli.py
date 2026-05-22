"""CLI integration tests via Typer's CliRunner (HTTP mocked)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from globeye.cli.app import app
from globeye.config import Settings, get_settings

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def cli_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        cache_enabled=False,
        http_max_retries=0,
        proxy_url=None,
        db_url=f"sqlite:///{tmp_path}/cli.db",
    )


def _mock_domain_sources(respx_mock, load_fixture) -> None:
    respx_mock.get("https://crt.sh/").mock(
        return_value=httpx.Response(200, json=load_fixture("crtsh_example_com.json"))
    )
    for url in (
        "https://rdap.org/domain/example.com",
        "https://otx.alienvault.com/api/v1/indicators/domain/example.com/passive_dns",
        "https://web.archive.org/cdx/search/cdx",
    ):
        respx_mock.get(url).mock(return_value=httpx.Response(200, json={}))


def test_cli_version():
    res = runner.invoke(app, ["version"])
    assert res.exit_code == 0
    assert "globeye" in res.stdout


def test_cli_sources_listing(cli_settings, monkeypatch):
    monkeypatch.setattr("globeye.cli.app.get_settings", lambda: cli_settings)
    res = runner.invoke(app, ["sources"])
    assert res.exit_code == 0
    assert "crtsh" in res.stdout


def test_cli_invalid_target_exit_2(cli_settings, monkeypatch):
    monkeypatch.setattr("globeye.cli.app.get_settings", lambda: cli_settings)
    res = runner.invoke(app, ["scan", "   "])
    assert res.exit_code == 2
    assert "invalid target" in res.stdout


def test_cli_scan_domain(tmp_path, load_fixture, respx_mock, cli_settings, monkeypatch):
    monkeypatch.setattr("globeye.cli.app.get_settings", lambda: cli_settings)
    _mock_domain_sources(respx_mock, load_fixture)
    out = tmp_path / "report.json"
    res = runner.invoke(app, ["scan", "example.com", "--no-cache", "--json", str(out)])
    assert res.exit_code == 0, res.stdout
    assert "example.com" in res.stdout
    data = json.loads(out.read_text())
    values = {f["value"] for f in data["findings"]}
    assert "api.example.com" in values
    assert data["summary"]["findings"]["total"] >= 4


def test_cli_scan_with_case_id(tmp_path, load_fixture, respx_mock, cli_settings, monkeypatch):
    monkeypatch.setattr("globeye.cli.app.get_settings", lambda: cli_settings)
    from sqlmodel import Session

    from globeye.core.db import make_engine
    from globeye.db.models import Case

    engine = make_engine(cli_settings.db_url)
    with Session(engine) as session:
        session.add(Case(title="CLI case", status="open"))
        session.commit()

    _mock_domain_sources(respx_mock, load_fixture)
    res = runner.invoke(app, ["scan", "example.com", "--no-cache", "--case-id", "1"])
    assert res.exit_code == 0, res.stdout
    assert "case:" in res.stdout
    assert "api.example.com" in res.stdout
