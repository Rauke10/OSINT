"""Informational performance benchmarks (non-gating)."""

from __future__ import annotations

import pytest

from globeye.core.models import Confidence, Finding
from globeye.core.orchestrator import Orchestrator


def _findings(n: int) -> list[Finding]:
    return [
        Finding(
            source="crtsh",
            target="example.com",
            confidence=Confidence.LOW,
            kind="subdomain",
            value=f"host{i}.example.com",
        )
        for i in range(n)
    ]


@pytest.mark.benchmark
def test_dedup_scales_to_10k_findings(benchmark):
    """Deduplicating 15k findings (10k unique + 5k dupes) stays fast."""
    findings = _findings(10_000)
    findings = findings + findings[:5_000]
    result = benchmark(Orchestrator._dedup, findings)
    assert len(result) == 10_000
