"""Shared pytest fixtures.

Tests are hermetic: ``Settings(_env_file=None)`` so no real ``.env`` is read,
and all HTTP is mocked with ``respx`` (no test performs real network I/O).
Fixtures in ``tests/fixtures`` are sanitized — no real keys, IPs or PII.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from globeye.config import Settings
from globeye.core.context import ScanContext

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def load_fixture() -> Callable[[str], Any]:
    def _load(name: str) -> Any:
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    return _load


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        cache_dir=str(tmp_path / "cache"),
        cache_enabled=True,
        http_max_retries=1,
        db_url=f"sqlite:///{tmp_path}/globeye.db",
    )


@pytest.fixture
def ctx(settings: Settings) -> ScanContext:
    return ScanContext.create(settings)


@pytest.fixture
def ctx_factory(tmp_path: Path) -> Callable[..., ScanContext]:
    """Build a ScanContext with extra Settings overrides (e.g. API keys)."""

    def _make(**overrides: Any) -> ScanContext:
        s = Settings(
            _env_file=None,
            cache_dir=str(tmp_path / "cache"),
            cache_enabled=False,
            http_max_retries=1,
            **overrides,
        )
        return ScanContext.create(s)

    return _make
