"""Unit tests for smart source routing (Fase 2B)."""

from __future__ import annotations

import pytest

from globeye.config import Settings
from globeye.core.source_profiles import ScanDepth
from globeye.core.target import detect
from globeye.services.source_router import effective_pivot, plan_routing


@pytest.fixture
def bare_settings() -> Settings:
    return Settings(_env_file=None)


def test_domain_standard_includes_keyless_and_keyed(bare_settings: Settings):
    plan = plan_routing(bare_settings, detect("example.com"), depth=ScanDepth.STANDARD)
    names = {e.source for e in plan.will_run} | {e.source for e in plan.skipped_missing_key}
    assert "rdap" in names
    assert "crtsh" in names
    assert plan.target_type == "domain"
    assert plan.profile == "domain_passive_intel"


def test_ip_excludes_domain_only_sources(bare_settings: Settings):
    plan = plan_routing(bare_settings, detect("8.8.8.8"), depth=ScanDepth.STANDARD)
    will = {e.source for e in plan.will_run}
    skipped = {e.source for e in plan.skipped_missing_key}
    assert "crtsh" not in will
    assert "crtsh" not in skipped
    assert "hunter" not in will
    na = {e.source for e in plan.not_applicable}
    assert "crtsh" in na or "hunter" in na
    assert "rdap" in will or "rdap" in skipped


def test_email_profile(bare_settings: Settings):
    plan = plan_routing(bare_settings, detect("test@example.com"), depth=ScanDepth.STANDARD)
    names = {e.source for e in plan.will_run} | {e.source for e in plan.skipped_missing_key}
    assert "hibp" in names or "gravatar" in names
    hunter_na = [e for e in plan.not_applicable if e.source == "hunter"]
    assert hunter_na, "hunter should be not_applicable for email"


def test_phone_no_technical_sources(bare_settings: Settings):
    plan = plan_routing(bare_settings, detect("+34600111222"), depth=ScanDepth.STANDARD)
    assert plan.will_run == []
    assert plan.skipped_missing_key == []
    assert any("teléfono" in w for w in plan.warnings)


def test_person_sensitive_warning(bare_settings: Settings):
    plan = plan_routing(bare_settings, detect("Jane Doe"), depth=ScanDepth.STANDARD)
    assert plan.will_run == []
    assert any("sensible" in w for w in plan.warnings)


def test_missing_key_in_skipped_not_not_applicable(bare_settings: Settings):
    plan = plan_routing(bare_settings, detect("8.8.8.8"), depth=ScanDepth.STANDARD)
    skipped = {e.source for e in plan.skipped_missing_key}
    if "shodan" in skipped:
        assert "shodan" not in {e.source for e in plan.not_applicable}


def test_quick_excludes_paid_sources(bare_settings: Settings):
    plan = plan_routing(bare_settings, detect("example.com"), depth=ScanDepth.QUICK)
    will = {e.source for e in plan.will_run}
    assert "shodan" not in will
    assert "rdap" in will
    assert "crtsh" in will


def test_deep_includes_github_pastebin_when_configured(bare_settings: Settings):
    plan = plan_routing(bare_settings, detect("example.com"), depth=ScanDepth.DEEP)
    names = {e.source for e in plan.will_run} | {e.source for e in plan.skipped_missing_key}
    assert "github" in names or "pastebin" in names


def test_selected_sources_filters_profile(bare_settings: Settings):
    plan = plan_routing(
        bare_settings,
        detect("example.com"),
        depth=ScanDepth.STANDARD,
        selected_sources=["rdap", "crtsh"],
    )
    assert {e.source for e in plan.will_run} <= {"rdap", "crtsh"}


def test_effective_pivot_quick_disables_pivot():
    pivot, depth = effective_pivot(ScanDepth.QUICK, True)
    assert pivot is False
    assert depth == 0


def test_cidr_warning(bare_settings: Settings):
    plan = plan_routing(bare_settings, detect("10.0.0.0/24"), depth=ScanDepth.STANDARD)
    assert plan.will_run == []
    assert any("CIDR" in w for w in plan.warnings)
