"""Data Explorer trace fields and CSV audit columns (Fase 2C.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from globeye.core.db import make_engine
from globeye.services.case_data import build_case_data
from tests.unit.test_case_data import _seed_case


@pytest.fixture
def engine(tmp_path: Path):
    return make_engine(f"sqlite:///{tmp_path}/de_trace.db")


def test_items_include_trace_fields(engine):
    _seed_case(engine)
    payload = build_case_data(engine, 1, limit=5)
    row = payload["items"][0]
    assert "original_values" in row
    assert "normalization_reason" in row
    assert "canonical_key" in row or row.get("type") != "url"


def test_pagination_does_not_drop_total(engine):
    _seed_case(engine)
    p1 = build_case_data(engine, 1, limit=1, offset=0)
    p2 = build_case_data(engine, 1, limit=1, offset=1)
    assert p1["total_count"] == p2["total_count"]
    assert p1["visible_count"] == 1


def test_live_check_limit_independent(engine):
    _seed_case(engine)
    payload = build_case_data(engine, 1, limit=2000)
    assert payload["counts"]["wayback_entity_limit"] == 25
    assert payload["filtered_count"] >= payload["visible_count"]
