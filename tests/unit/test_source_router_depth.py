"""Routing buckets: skipped_by_depth vs not_applicable."""

from __future__ import annotations

from globeye.config import Settings
from globeye.core.source_profiles import ScanDepth
from globeye.core.target import detect
from globeye.services.source_router import plan_routing


def test_shodan_skipped_by_depth_on_quick_domain_scan():
    settings = Settings(_env_file=None)
    target = detect("example.com")
    plan = plan_routing(settings, target, depth=ScanDepth.QUICK)
    skipped = {e.source for e in plan.skipped_by_depth}
    assert "shodan" in skipped or "securitytrails" in skipped


def test_hibp_not_applicable_for_domain():
    settings = Settings(_env_file=None)
    target = detect("example.com")
    plan = plan_routing(settings, target, depth=ScanDepth.STANDARD)
    na = {e.source for e in plan.not_applicable}
    assert "hibp" in na
