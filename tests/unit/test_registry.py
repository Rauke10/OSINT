"""Structural invariants enforced across every registered source."""

from __future__ import annotations

from globeye.sources.base import discover_sources


def test_expected_sources_registered():
    names = {cls.name for cls in discover_sources()}
    assert {
        "crtsh",
        "rdap",
        "shodan",
        "censys",
        "securitytrails",
        "otx",
        "wayback",
    } <= names


def test_every_source_declares_a_tight_allowlist():
    for cls in discover_sources():
        assert cls.allowed_hosts, f"{cls.name} has no allowlist"
        assert cls.supported_target_types, f"{cls.name} supports no targets"
        # No allowlisted host may be a bare/example target placeholder.
        for host in cls.allowed_hosts:
            assert "example.com" not in host
            assert host == host.lower()


def test_source_names_are_unique():
    names = [cls.name for cls in discover_sources()]
    assert len(names) == len(set(names))
