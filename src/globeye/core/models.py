"""Shared Pydantic v2 models used across GLOBEYE.

These models are the contract between sources, the orchestrator, the
reporters and the API. Everything a source returns is a :class:`Finding`.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TargetType(enum.StrEnum):
    """The kind of entity a target represents."""

    DOMAIN = "domain"
    IP = "ip"
    ASN = "asn"
    CIDR = "cidr"
    CERT_HASH = "cert_hash"
    EMAIL = "email"
    USERNAME = "username"
    PHONE = "phone"
    PERSON = "person"
    ORG = "org"


class Confidence(enum.StrEnum):
    """How much we trust a finding."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Target(BaseModel):
    """A normalized scan target."""

    model_config = ConfigDict(frozen=True)

    raw: str
    type: TargetType
    value: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.type.value}:{self.value}"


class Evidence(BaseModel):
    """Raw, auditable evidence backing a finding."""

    source_url: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    raw: Any = None


class GraphNodeHint(BaseModel):
    """Hint for the relationship graph.

    ``node_id`` uniquely identifies the discovered entity; ``parent_id``
    (when present) creates an edge from the parent node to this node.
    """

    node_type: str
    node_id: str
    label: str
    parent_id: str | None = None


class Finding(BaseModel):
    """A single piece of information returned by a source."""

    source: str
    target: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confidence: Confidence
    kind: str
    value: str
    normalized_data: dict[str, Any] = Field(default_factory=dict)
    raw_evidence: Evidence | None = None
    graph_node_hint: GraphNodeHint | None = None
    pivot_target: Target | None = None

    def dedup_key(self) -> tuple[str, str, str]:
        """Identity used to collapse duplicate findings across sources."""
        return (self.kind, self.value.lower(), self.source)


class RateLimit(BaseModel):
    """Published rate limit for a source: ``rate`` requests per ``per`` seconds."""

    rate: float = 1.0
    per: float = 1.0
    concurrency: int = 2

    @property
    def min_interval(self) -> float:
        """Minimum seconds between two consecutive requests."""
        if self.rate <= 0:
            return 0.0
        return self.per / self.rate


class SourceStatus(BaseModel):
    """Result of a source health check."""

    name: str
    available: bool
    requires_api_key: bool
    has_api_key: bool
    detail: str | None = None


class ScanResult(BaseModel):
    """The full outcome of a scan."""

    target: Target
    started_at: datetime
    finished_at: datetime
    sources_used: list[str]
    sources_skipped: dict[str, str] = Field(default_factory=dict)
    findings: list[Finding]
    pivoted_targets: list[Target] = Field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()

    def summary(self) -> dict[str, int]:
        """Counts of findings by confidence level."""
        out: dict[str, int] = {c.value: 0 for c in Confidence}
        for f in self.findings:
            out[f.confidence.value] += 1
        out["total"] = len(self.findings)
        return out
