"""Breadth-first pivot queue with cycle protection."""

from __future__ import annotations

from globeye.core.models import Target, TargetType
from globeye.core.pivot import _PivotQueue


def _t(value: str, type_: TargetType = TargetType.DOMAIN) -> Target:
    return Target(raw=value, type=type_, value=value)


def test_starts_with_root_at_depth_zero():
    q = _PivotQueue(_t("example.com"))
    assert q  # truthy while non-empty
    target, depth = q.pop()
    assert target.value == "example.com"
    assert depth == 0
    assert not q  # empty after popping the root


def test_dedups_against_root_and_prior_adds():
    q = _PivotQueue(_t("example.com"))
    q.pop()
    assert q.add(_t("a.example.com"), 1) is True
    assert q.add(_t("a.example.com"), 1) is False  # already enqueued
    assert q.add(_t("example.com"), 1) is False  # equals the root


def test_is_breadth_first():
    q = _PivotQueue(_t("root.com"))
    q.pop()
    q.add(_t("a.com"), 1)
    q.add(_t("b.com"), 2)
    first, second = q.pop(), q.pop()
    assert (first[0].value, first[1]) == ("a.com", 1)
    assert (second[0].value, second[1]) == ("b.com", 2)
