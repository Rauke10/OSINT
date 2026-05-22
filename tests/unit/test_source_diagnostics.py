"""Source diagnostics UI categories (Fase 2C.3)."""

from __future__ import annotations

from globeye.config import Settings
from globeye.services.source_diagnostics import enrich_status_row


def test_missing_key_category():
    settings = Settings(_env_file=None)
    row = enrich_status_row(
        {"name": "shodan", "status": "missing_key", "requires_api_key": True, "message": "x"},
        settings,
    )
    assert row["ui_category"] == "missing_key"
    assert "SHODAN" in str(row.get("env_vars") or row.get("fix_hint") or "")


def test_not_applicable_not_error():
    settings = Settings(_env_file=None)
    row = enrich_status_row(
        {
            "name": "hibp",
            "status": "not_applicable",
            "requires_api_key": True,
            "message": "email only",
        },
        settings,
    )
    assert row["ui_category"] == "not_applicable"


def test_configured_not_checked_hint():
    settings = Settings(_env_file=None)
    row = enrich_status_row(
        {
            "name": "virustotal",
            "credential_status": "configured_not_checked",
            "status": "configured_not_checked",
            "requires_api_key": True,
            "message": "Credentials configured",
        },
        settings,
    )
    assert row["credential_status"] == "configured_not_checked"
    assert row["ui_category"] == "executed_ok"


def test_incompatible_censys():
    settings = Settings(_env_file=None)
    row = enrich_status_row(
        {
            "name": "censys",
            "credential_status": "incompatible_credentials",
            "status": "incompatible_credentials",
            "requires_api_key": True,
            "provider_error_message_sanitized": "Platform PAT not supported",
        },
        settings,
    )
    assert row["ui_category"] == "config_error"


def test_valid_no_results_ui_category():
    settings = Settings(_env_file=None)
    row = enrich_status_row(
        {
            "name": "shodan",
            "credential_status": "valid",
            "status": "ok",
            "probe_scan_status": "no_results",
            "requires_api_key": True,
            "findings_count": 0,
        },
        settings,
    )
    assert row["ui_category"] == "executed_empty"


def test_rate_limited_category():
    settings = Settings(_env_file=None)
    row = enrich_status_row(
        {
            "name": "virustotal",
            "credential_status": "rate_limited",
            "status": "rate_limited",
            "requires_api_key": True,
        },
        settings,
    )
    assert row["ui_category"] == "rate_limited"


def test_forbidden_uses_provider_message():
    settings = Settings(_env_file=None)
    row = enrich_status_row(
        {
            "name": "virustotal",
            "credential_status": "forbidden",
            "status": "forbidden",
            "requires_api_key": True,
            "provider_error_message_sanitized": "Insufficient privileges",
        },
        settings,
    )
    assert "Insufficient" in (row.get("how_to_fix") or "")


def test_blocked_by_passive_guard_category():
    settings = Settings(_env_file=None)
    row = enrich_status_row(
        {
            "name": "rdap",
            "credential_status": "blocked_by_passive_guard",
            "status": "blocked_by_passive_guard",
            "requires_api_key": False,
            "provider_error_message_sanitized": "Passive Guard blocked rdap.verisign.com",
        },
        settings,
    )
    assert row["ui_category"] == "config_error"
    assert "verisign" in (row.get("how_to_fix") or "")


def test_provider_timeout_category():
    settings = Settings(_env_file=None)
    row = enrich_status_row(
        {
            "name": "crtsh",
            "credential_status": "provider_timeout",
            "probe_scan_status": "provider_timeout",
            "status": "provider_timeout",
            "requires_api_key": False,
        },
        settings,
    )
    assert row["ui_category"] == "network_error"


def test_no_secrets_in_message():
    settings = Settings(_env_file=None, shodan_api_key="SUPER-SECRET-KEY-9999")
    row = enrich_status_row(
        {"name": "shodan", "status": "ok", "requires_api_key": True, "message": "ok"},
        settings,
    )
    hint = str(row.get("masked_hint") or "")
    assert "SUPER-SECRET" not in hint
    if hint:
        assert hint.startswith("****")
