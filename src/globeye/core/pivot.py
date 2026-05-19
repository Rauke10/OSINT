"""Pivot logic: turn discovered entities into follow-up passive scans.

The classic chain is *domain → related emails → usernames on public
profiles*. We honour an explicit ``Finding.pivot_target`` and additionally
derive pivots from high-value finding kinds, deduplicating the result.
"""

from __future__ import annotations

from collections.abc import Iterable

from globeye.core.models import Finding, Target, TargetType

_EMAIL_KINDS = {"email", "contact_email"}
_USERNAME_KINDS = {"username"}


def derive_pivots(findings: Iterable[Finding]) -> list[Target]:
    """Return de-duplicated pivot targets from a batch of findings."""
    out: list[Target] = []
    seen: set[tuple[str, str]] = set()

    def _add(target: Target) -> None:
        key = (target.type.value, target.value)
        if key not in seen:
            seen.add(key)
            out.append(target)

    for f in findings:
        if f.pivot_target is not None:
            _add(f.pivot_target)
        elif f.kind in _EMAIL_KINDS and "@" in f.value:
            _add(
                Target(
                    raw=f.value,
                    type=TargetType.EMAIL,
                    value=f.value.lower(),
                )
            )
        elif f.kind in _USERNAME_KINDS and f.value:
            _add(Target(raw=f.value, type=TargetType.USERNAME, value=f.value))
    return out
