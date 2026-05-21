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


class _PivotQueue:
    """Breadth-first queue of targets to scan, with cycle protection.

    Each target is scanned at most once. ``add`` returns ``False`` when the
    target was already seen, so callers can record only genuine new pivots.
    """

    def __init__(self, root: Target) -> None:
        self._seen: set[tuple[str, str]] = {(root.type.value, root.value)}
        self._items: list[tuple[Target, int]] = [(root, 0)]

    def __bool__(self) -> bool:
        return bool(self._items)

    def pop(self) -> tuple[Target, int]:
        """Remove and return the next ``(target, depth)`` (FIFO)."""
        return self._items.pop(0)

    def add(self, target: Target, depth: int) -> bool:
        """Enqueue ``target`` unless already seen. Returns whether it was new."""
        key = (target.type.value, target.value)
        if key in self._seen:
            return False
        self._seen.add(key)
        self._items.append((target, depth))
        return True
