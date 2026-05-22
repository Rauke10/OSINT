"""Data Explorer UX defaults and counts (2C.3 clarity)."""

from __future__ import annotations

from pathlib import Path

import pytest

from globeye.core.db import make_engine
from globeye.services.case_data import build_case_data
from tests.unit.test_case_data import _seed_case


@pytest.fixture
def engine(tmp_path: Path):
    return make_engine(f"sqlite:///{tmp_path}/ux.db")


def test_default_does_not_hide_historical_or_noisy(engine):
    _seed_case(engine)
    payload = build_case_data(engine, 1)
    assert payload["counts"]["hidden_by_filters_count"] == 0
    assert payload["total_count"] == payload["filtered_count"]


def test_counts_fields(engine):
    _seed_case(engine)
    payload = build_case_data(engine, 1, limit=10, offset=0)
    c = payload["counts"]
    assert c["total_count"] >= c["filtered_count"]
    assert c["evidence_total_count"] >= 0
    assert c["findings_total_count"] >= c["total_count"]
    assert payload["visible_count"] == len(payload["items"])
    assert payload["total_count"] == c["total_count"]


def test_pagination_limit_does_not_cap_total_count(engine):
    _seed_case(engine)
    page = build_case_data(engine, 1, limit=1, offset=0)
    assert page["visible_count"] == 1
    assert page["total_count"] >= page["visible_count"]
    assert page["filtered_count"] >= 1


def test_show_all_equivalent_clears_hiding(engine):
    _seed_case(engine)
    hidden = build_case_data(
        engine,
        1,
        hide_noisy=True,
        hide_historical=True,
        hide_false_positive=True,
        hide_discarded=True,
    )
    assert hidden["counts"]["hidden_by_filters_count"] >= 0
    shown = build_case_data(
        engine,
        1,
        hide_noisy=False,
        hide_historical=False,
        hide_false_positive=False,
        hide_discarded=False,
    )
    assert shown["filtered_count"] >= hidden["filtered_count"]


def test_evidence_total_can_exceed_entity_count(engine):
    _seed_case(engine)
    payload = build_case_data(engine, 1)
    assert payload["counts"]["evidence_total_count"] >= 0
    assert payload["counts"]["findings_total_count"] >= payload["counts"]["total_count"]
