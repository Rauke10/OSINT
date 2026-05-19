"""Smoke test: the package imports and exposes its version."""

import globeye


def test_package_version() -> None:
    assert globeye.__version__ == "0.1.0"
