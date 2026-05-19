"""Redaction: configured secrets and pattern secrets never reach logs."""

from __future__ import annotations

from globeye.config import Settings
from globeye.utils.redact import Redactor, structlog_redactor


def test_redactor_masks_known_secret():
    r = Redactor({"S3cr3t-Key-Value"})
    out = r.scrub("Authorization: Bearer S3cr3t-Key-Value")
    assert "S3cr3t-Key-Value" not in out
    assert "****" in out


def test_redactor_masks_patterns_in_nested_structures():
    r = Redactor()
    scrubbed = r.scrub(
        {"url": "https://api.example/?token=abcdef123456", "list": ["ghp_" + "a" * 30]}
    )
    assert "abcdef123456" not in scrubbed["url"]
    assert "ghp_" not in scrubbed["list"][0]


def test_settings_secret_values_feed_redactor():
    s = Settings(_env_file=None, shodan_api_key="MY-SHODAN-KEY")
    assert "MY-SHODAN-KEY" in s.secret_values()


def test_structlog_processor_redacts_event():
    s = Settings(_env_file=None, github_token="ghp_" + "z" * 36)
    processor = structlog_redactor(Redactor(s.secret_values()))
    event = processor(None, "info", {"event": "calling", "token": "ghp_" + "z" * 36})
    assert "ghp_" not in str(event["token"])
    assert "****" in str(event["token"])
