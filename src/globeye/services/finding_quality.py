"""Finding and entity quality labels for analyst review (Fase 2B.1)."""

from __future__ import annotations

import json
from collections import defaultdict
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from globeye.core.db import ScanRecord
from globeye.core.models import Finding, ScanResult, Target, TargetType
from globeye.db.models import Entity, ScanJob

# Align with wayback.CDX_FETCH_LIMIT — URLs beyond this in CDX total are noisy summary only.
WAYBACK_SCAN_CAP = 200
WAYBACK_UI_LIMIT = WAYBACK_SCAN_CAP
# Live-check batch only (not entity/inventory cap).
WAYBACK_ENTITY_LIMIT = 25


class QualityLabel(StrEnum):
    VERIFIED = "verified"
    LIKELY = "likely"
    HISTORICAL = "historical"
    UNVERIFIED = "unverified"
    NOISY = "noisy"
    POSSIBLE_FALSE_POSITIVE = "possible_false_positive"


TRUSTED_SOURCES = frozenset(
    {
        "rdap",
        "crtsh",
        "shodan",
        "virustotal",
        "abuseipdb",
        "securitytrails",
        "censys",
        "hibp",
        "otx",
    }
)
HISTORICAL_SOURCES = frozenset({"wayback"})
HISTORICAL_KINDS = frozenset({"archived_url", "wayback_summary"})
NOISY_SOURCES = frozenset({"wayback", "github", "pastebin"})


class FindingQualityMeta(BaseModel):
    quality_label: str
    confidence_score: int = Field(ge=0, le=100)
    verification_sources_count: int = 0
    is_historical: bool = False
    is_potential_false_positive: bool = False
    quality_reason: str = ""


def _entity_key(kind: str, value: str) -> tuple[str, str]:
    k = kind.lower()
    if k in {"email", "domain", "subdomain", "username"}:
        return k, value.lower()
    if k in {"url", "archived_url"}:
        from globeye.services.url_normalization import normalize_url_for_entity

        return k, normalize_url_for_entity(value).normalized_value
    return k, value


def _source_groups(findings: list[Finding]) -> dict[tuple[str, str], set[str]]:
    groups: dict[tuple[str, str], set[str]] = defaultdict(set)
    for f in findings:
        if f.kind in HISTORICAL_KINDS and f.kind != "wayback_summary":
            continue
        groups[_entity_key(f.kind, f.value)].add(f.source)
    return groups


def _target_domain(target: Target) -> str | None:
    if target.type is TargetType.DOMAIN:
        return target.value.lower()
    if target.type is TargetType.EMAIL and "@" in target.value:
        return target.value.split("@", 1)[1].lower()
    return None


def _is_weak_relation(finding: Finding, target: Target) -> bool:
    val = finding.value.lower().strip()
    tv = target.value.lower().strip()
    tdom = _target_domain(target)

    if finding.kind in {"archived_url", "wayback_summary"}:
        return bool(tdom and tdom not in val)

    if finding.kind in {"subdomain", "domain"}:
        if val == tv or (tdom and (val == tdom or val.endswith(f".{tdom}"))):
            return False
        if tdom and tdom in val and val != tdom:
            return False
        if tdom and abs(len(val) - len(tdom)) <= 3 and tdom[:4] in val:
            return True
        if tdom and tdom not in val:
            return True

    if finding.kind == "email" and tdom:
        local, _, dom = val.partition("@")
        if not local or dom != tdom:
            return True

    return bool(
        finding.kind in {"note", "code_match", "paste"}
        and tv not in val
        and (tdom is None or tdom not in val)
    )


def classify_finding(
    finding: Finding,
    *,
    target: Target,
    source_counts: dict[tuple[str, str], set[str]],
    wayback_total: int = 0,
) -> FindingQualityMeta:
    key = _entity_key(finding.kind, finding.value)
    sources = source_counts.get(key, {finding.source})
    n_sources = len(sources)

    if finding.kind == "wayback_summary":
        return FindingQualityMeta(
            quality_label=QualityLabel.HISTORICAL.value,
            confidence_score=40,
            is_historical=True,
            quality_reason="Resumen de URLs históricas archivadas",
        )

    if finding.source in HISTORICAL_SOURCES or finding.kind in HISTORICAL_KINDS:
        label = QualityLabel.HISTORICAL
        if wayback_total > WAYBACK_UI_LIMIT or finding.normalized_data.get("wayback_truncated"):
            label = QualityLabel.NOISY
        return FindingQualityMeta(
            quality_label=label.value,
            confidence_score=35 if label is QualityLabel.NOISY else 45,
            verification_sources_count=n_sources,
            is_historical=True,
            quality_reason="Dato histórico (Wayback / archivo)",
        )

    if _is_weak_relation(finding, target):
        return FindingQualityMeta(
            quality_label=QualityLabel.POSSIBLE_FALSE_POSITIVE.value,
            confidence_score=25,
            verification_sources_count=n_sources,
            is_potential_false_positive=True,
            quality_reason="Relación débil o valor no alineado con el objetivo",
        )

    if n_sources >= 2:
        return FindingQualityMeta(
            quality_label=QualityLabel.VERIFIED.value,
            confidence_score=min(95, 70 + n_sources * 8),
            verification_sources_count=n_sources,
            quality_reason=f"Encontrado por {n_sources} fuentes independientes",
        )

    if finding.source in NOISY_SOURCES and finding.confidence.value == "low":
        return FindingQualityMeta(
            quality_label=QualityLabel.NOISY.value,
            confidence_score=30,
            verification_sources_count=1,
            quality_reason=f"Fuente con mucho ruido potencial ({finding.source})",
        )

    if finding.source in TRUSTED_SOURCES and finding.confidence.value in {"high", "medium"}:
        return FindingQualityMeta(
            quality_label=QualityLabel.LIKELY.value,
            confidence_score=65 if finding.confidence.value == "medium" else 78,
            verification_sources_count=1,
            quality_reason=f"Fuente fiable ({finding.source}) sin confirmación cruzada",
        )

    return FindingQualityMeta(
        quality_label=QualityLabel.UNVERIFIED.value,
        confidence_score=45,
        verification_sources_count=1,
        quality_reason="Solo aparece en una fuente; sin confirmación adicional",
    )


def annotate_findings(findings: list[Finding], target: Target) -> list[Finding]:
    """Attach quality metadata under ``normalized_data['quality']`` (non-destructive)."""
    groups = _source_groups(findings)
    wayback_total = sum(1 for f in findings if f.source == "wayback" and f.kind == "archived_url")
    if not wayback_total and findings:
        for f in findings:
            if f.kind == "wayback_summary":
                wayback_total = int(f.normalized_data.get("total_urls", 0))
                break

    out: list[Finding] = []
    for f in findings:
        meta = classify_finding(f, target=target, source_counts=groups, wayback_total=wayback_total)
        copy = f.model_copy(deep=True)
        copy.normalized_data["quality"] = meta.model_dump()
        out.append(copy)
    return out


def annotate_scan_result(result: ScanResult) -> ScanResult:
    """Enrich scan findings with quality metadata."""
    result.findings = annotate_findings(result.findings, result.target)
    return result


def load_case_findings(engine: Engine, case_id: int) -> list[tuple[Finding, Target]]:
    """Load findings from completed jobs with their scan targets."""
    pairs: list[tuple[Finding, Target]] = []
    with Session(engine) as session:
        jobs = list(
            session.exec(
                select(ScanJob)
                .where(ScanJob.case_id == case_id)
                .where(ScanJob.status == "completed")
            ).all()
        )
        for job in jobs:
            if not job.scan_record_id:
                continue
            record = session.get(ScanRecord, job.scan_record_id)
            if record is None:
                continue
            try:
                payload = json.loads(record.result_json)
            except json.JSONDecodeError:
                continue
            target_data = payload.get("target") or {}
            target = Target(
                raw=job.target_raw,
                type=TargetType(str(target_data.get("type", job.target_type))),
                value=str(target_data.get("value", job.target_value)),
            )
            for raw in payload.get("findings", []):
                pairs.append((Finding.model_validate(raw), target))
    return pairs


def classify_entity_from_findings(
    entity_type: str,
    normalized_value: str,
    related: list[FindingQualityMeta],
) -> FindingQualityMeta:
    if not related:
        return FindingQualityMeta(
            quality_label=QualityLabel.UNVERIFIED.value,
            confidence_score=40,
            quality_reason="Sin hallazgos vinculados",
        )
    priority = [
        QualityLabel.VERIFIED,
        QualityLabel.LIKELY,
        QualityLabel.HISTORICAL,
        QualityLabel.UNVERIFIED,
        QualityLabel.NOISY,
        QualityLabel.POSSIBLE_FALSE_POSITIVE,
    ]
    best = related[0]
    for label in priority:
        for m in related:
            if m.quality_label == label.value:
                best = m
                break
        else:
            continue
        break
    if entity_type == "url" and any(m.is_historical for m in related):
        return FindingQualityMeta(
            quality_label=QualityLabel.HISTORICAL.value,
            confidence_score=40,
            is_historical=True,
            quality_reason="URL histórica (Wayback)",
        )
    return best


def _finding_matches_entity(finding: Finding, entity_type: str, normalized_value: str) -> bool:
    if entity_type == "url" and finding.kind == "archived_url":
        return finding.value.lower() == normalized_value.lower()
    fk, fv = _entity_key(finding.kind, finding.value)
    return fk == entity_type and fv == normalized_value


def quality_for_entity(
    engine: Engine,
    case_id: int,
    *,
    entity_type: str,
    normalized_value: str,
) -> FindingQualityMeta:
    pairs = load_case_findings(engine, case_id)
    all_findings = [f for f, _ in pairs]
    related_meta: list[FindingQualityMeta] = []
    for finding, target in pairs:
        if not _finding_matches_entity(finding, entity_type, normalized_value):
            continue
        groups = _source_groups(all_findings)
        related_meta.append(
            classify_finding(
                finding,
                target=target,
                source_counts=groups,
                wayback_total=sum(1 for x in all_findings if x.kind == "archived_url"),
            )
        )
    return classify_entity_from_findings(entity_type, normalized_value, related_meta)


def build_case_quality_summary(engine: Engine, case_id: int) -> dict[str, Any]:
    """Aggregate quality counts for a case."""
    pairs = load_case_findings(engine, case_id)
    all_findings = [f for f, _ in pairs]
    by_entity_meta: dict[tuple[str, str], list[FindingQualityMeta]] = defaultdict(list)

    for finding, target in pairs:
        groups = _source_groups(all_findings)
        wayback_total = sum(1 for x in all_findings if x.kind == "archived_url")
        meta = classify_finding(
            finding, target=target, source_counts=groups, wayback_total=wayback_total
        )
        ek = _entity_key(finding.kind, finding.value)
        by_entity_meta[ek].append(meta)

    with Session(engine) as session:
        db_entities = list(session.exec(select(Entity).where(Entity.case_id == case_id)).all())
        entity_total = len(db_entities)

    label_counts: dict[str, int] = defaultdict(int)
    for ent in db_entities:
        q = quality_for_entity(
            engine,
            case_id,
            entity_type=ent.entity_type,
            normalized_value=ent.normalized_value,
        )
        label_counts[q.quality_label] += 1

    finding_labels: dict[str, int] = defaultdict(int)
    verified_by_source: dict[str, int] = defaultdict(int)
    noise_by_source: dict[str, int] = defaultdict(int)

    for finding, target in pairs:
        groups = _source_groups(all_findings)
        meta = classify_finding(finding, target=target, source_counts=groups, wayback_total=0)
        finding_labels[meta.quality_label] += 1
        if meta.quality_label == QualityLabel.VERIFIED.value:
            verified_by_source[finding.source] += 1
        if meta.quality_label in {
            QualityLabel.NOISY.value,
            QualityLabel.POSSIBLE_FALSE_POSITIVE.value,
        }:
            noise_by_source[finding.source] += 1

    return {
        "case_id": case_id,
        "total_entities": entity_total,
        "total_findings": len(all_findings),
        "entities_by_label": dict(label_counts),
        "findings_by_label": dict(finding_labels),
        "top_sources_verified": sorted(verified_by_source.items(), key=lambda x: -x[1])[:8],
        "top_sources_noise": sorted(noise_by_source.items(), key=lambda x: -x[1])[:8],
    }
