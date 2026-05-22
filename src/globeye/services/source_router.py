"""Smart source selection by target type and scan depth (Fase 2B)."""

from __future__ import annotations

from dataclasses import dataclass, field

from globeye.config import Settings
from globeye.core.models import Target, TargetType
from globeye.core.source_profiles import (
    SOURCE_SPECS,
    ScanDepth,
    profile_id_for,
    profile_source_names,
    reason_not_applicable,
    source_spec,
    special_target_warning,
)
from globeye.services.source_credentials import is_configured
from globeye.sources.base import PassiveSource, discover_sources
from globeye.sources.catalog import label_for


@dataclass(frozen=True, slots=True)
class RoutedSourceEntry:
    source: str
    reason: str
    requires_key: bool
    configured: bool = True
    label: str = ""


@dataclass(frozen=True, slots=True)
class RoutingPlan:
    """Outcome of routing — no HTTP calls are made."""

    target_type: str
    normalized_value: str
    profile: str
    depth: str
    will_run: list[RoutedSourceEntry] = field(default_factory=list)
    skipped_missing_key: list[RoutedSourceEntry] = field(default_factory=list)
    skipped_by_depth: list[RoutedSourceEntry] = field(default_factory=list)
    disabled: list[RoutedSourceEntry] = field(default_factory=list)
    not_applicable: list[RoutedSourceEntry] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def source_names_to_run(self) -> frozenset[str]:
        return frozenset(e.source for e in self.will_run)

    def to_preview_dict(self) -> dict[str, object]:
        return {
            "target_type": self.target_type,
            "normalized_value": self.normalized_value,
            "profile": self.profile,
            "depth": self.depth,
            "will_run": [_entry_dict(e) for e in self.will_run],
            "skipped_missing_key": [_entry_dict(e) for e in self.skipped_missing_key],
            "skipped_by_depth": [_entry_dict(e) for e in self.skipped_by_depth],
            "disabled": [_entry_dict(e) for e in self.disabled],
            "not_applicable": [_entry_dict(e) for e in self.not_applicable],
            "warnings": list(self.warnings),
        }


def _entry_dict(entry: RoutedSourceEntry) -> dict[str, object]:
    out: dict[str, object] = {
        "source": entry.source,
        "reason": entry.reason,
        "requires_key": entry.requires_key,
    }
    if entry.label:
        out["label"] = entry.label
    if entry.requires_key:
        out["configured"] = entry.configured
    return out


def _entry(
    name: str,
    *,
    reason: str,
    requires_key: bool,
    configured: bool = True,
) -> RoutedSourceEntry:
    label, _ = label_for(name)
    return RoutedSourceEntry(
        source=name,
        label=label,
        reason=reason,
        requires_key=requires_key,
        configured=configured,
    )


def _compatible(cls: type[PassiveSource], target: Target) -> bool:
    return target.type in cls.supported_target_types


def plan_routing(
    settings: Settings,
    target: Target,
    *,
    depth: ScanDepth | str = ScanDepth.STANDARD,
    selected_sources: list[str] | None = None,
) -> RoutingPlan:
    """Return applicable sources and exclusions without executing scans."""
    if isinstance(depth, str):
        depth = ScanDepth(depth)

    profile = profile_id_for(target.type)
    warnings: list[str] = []
    if msg := special_target_warning(target.type):
        warnings.append(msg)

    profile_names = profile_source_names(target.type, depth)
    if selected_sources:
        allowed = {s.strip().lower() for s in selected_sources if s.strip()}
        profile_names = [n for n in profile_names if n in allowed]

    will_run: list[RoutedSourceEntry] = []
    skipped_missing_key: list[RoutedSourceEntry] = []

    classes_by_name = {cls.name: cls for cls in discover_sources()}

    not_applicable: list[RoutedSourceEntry] = []
    skipped_by_depth: list[RoutedSourceEntry] = []
    disabled: list[RoutedSourceEntry] = []

    for name in profile_names:
        cls = classes_by_name.get(name)
        if cls is None:
            continue
        spec = source_spec(name)
        reason = spec.run_reason if spec else label_for(name)[1] or name
        requires_key = cls.requires_api_key
        configured = is_configured(settings, name, requires_api_key=requires_key)

        if not _compatible(cls, target):
            not_applicable.append(
                _entry(
                    name,
                    reason=reason_not_applicable(target.type, name),
                    requires_key=requires_key,
                    configured=configured,
                )
            )
            continue

        if requires_key and not configured:
            skipped_missing_key.append(
                _entry(
                    name,
                    reason="API key missing or not configured in .env",
                    requires_key=True,
                    configured=False,
                )
            )
            continue

        will_run.append(
            _entry(name, reason=reason, requires_key=requires_key, configured=configured)
        )

    if target.type not in (TargetType.PHONE, TargetType.PERSON, TargetType.CIDR):
        categorized = (
            {e.source for e in will_run}
            | {e.source for e in skipped_missing_key}
            | {e.source for e in not_applicable}
            | {e.source for e in skipped_by_depth}
            | {e.source for e in disabled}
        )
        for cls in discover_sources():
            name = cls.name
            if name in categorized:
                continue
            spec = source_spec(name) or SOURCE_SPECS.get(name)
            requires_key = cls.requires_api_key
            configured = is_configured(settings, name, requires_api_key=requires_key)
            if spec is not None and not spec.enabled:
                disabled.append(
                    _entry(
                        name,
                        reason="Fuente deshabilitada en configuración",
                        requires_key=requires_key,
                        configured=configured,
                    )
                )
                continue
            if spec is not None and depth not in spec.depth_levels and _compatible(cls, target):
                levels = ", ".join(sorted(d.value for d in spec.depth_levels))
                skipped_by_depth.append(
                    _entry(
                        name,
                        reason=f"Solo se usa en profundidad: {levels}",
                        requires_key=requires_key,
                        configured=configured,
                    )
                )
                continue
            not_applicable.append(
                _entry(
                    name,
                    reason=reason_not_applicable(target.type, name),
                    requires_key=requires_key,
                    configured=configured,
                )
            )

    if depth is ScanDepth.DEEP and target.type in {
        TargetType.DOMAIN,
        TargetType.EMAIL,
        TargetType.IP,
    }:
        warnings.append(
            "Profundidad «deep» puede consumir cuota en APIs de pago y búsquedas indexadas."
        )

    return RoutingPlan(
        target_type=target.type.value,
        normalized_value=target.value,
        profile=profile,
        depth=depth.value,
        will_run=will_run,
        skipped_missing_key=skipped_missing_key,
        skipped_by_depth=sorted(skipped_by_depth, key=lambda e: e.source),
        disabled=sorted(disabled, key=lambda e: e.source),
        not_applicable=sorted(not_applicable, key=lambda e: e.source),
        warnings=warnings,
    )


def effective_pivot(depth: ScanDepth | str, pivot_requested: bool) -> tuple[bool, int]:
    """Map depth to pivot flag and max pivot depth."""
    if isinstance(depth, str):
        depth = ScanDepth(depth)
    if depth is ScanDepth.QUICK:
        return False, 0
    if depth is ScanDepth.STANDARD:
        return pivot_requested, 1 if pivot_requested else 0
    return pivot_requested, 1
