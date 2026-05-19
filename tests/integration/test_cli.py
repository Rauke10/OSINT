"""CLI integration tests via Typer's CliRunner (HTTP mocked)."""

from __future__ import annotations

import json

import httpx
from typer.testing import CliRunner

from globeye.cli.app import app

runner = CliRunner()


def test_cli_version():
    res = runner.invoke(app, ["version"])
    assert res.exit_code == 0
    assert "globeye" in res.stdout


def test_cli_sources_listing():
    res = runner.invoke(app, ["sources"])
    assert res.exit_code == 0
    assert "crtsh" in res.stdout


def test_cli_invalid_target_exit_2():
    res = runner.invoke(app, ["scan", "   "])
    assert res.exit_code == 2
    assert "invalid target" in res.stdout


def test_cli_scan_domain(tmp_path, load_fixture, respx_mock):
    respx_mock.get("https://crt.sh/").mock(
        return_value=httpx.Response(200, json=load_fixture("crtsh_example_com.json"))
    )
    out = tmp_path / "report.json"
    res = runner.invoke(app, ["scan", "example.com", "--no-cache", "--json", str(out)])
    assert res.exit_code == 0, res.stdout
    assert "example.com" in res.stdout
    data = json.loads(out.read_text())
    values = {f["value"] for f in data["findings"]}
    assert "api.example.com" in values
    assert data["summary"]["findings"]["total"] >= 4
