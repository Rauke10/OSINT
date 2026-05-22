"""VirusTotal API v3 — passive DNS and analysis stats (no active scanning)."""

from __future__ import annotations

from typing import Any, ClassVar

from globeye.core.models import (
    Confidence,
    Evidence,
    Finding,
    GraphNodeHint,
    RateLimit,
    Target,
    TargetType,
)
from globeye.sources.base import PassiveSource, register

_BASE = "https://www.virustotal.com/api/v3"


@register
class VirusTotalSource(PassiveSource):
    """VirusTotal object lookup for domains and IPs."""

    name: ClassVar[str] = "virustotal"
    requires_api_key: ClassVar[bool] = True
    supported_target_types: ClassVar[set[TargetType]] = {
        TargetType.DOMAIN,
        TargetType.IP,
    }
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=4, per=60, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"www.virustotal.com"}

    def api_key(self) -> str | None:
        key = self.ctx.settings.virustotal_api_key
        return key.get_secret_value() if key else None

    async def fetch(self, target: Target) -> list[Finding]:
        key = self.api_key()
        if not key:
            return []
        headers = {"x-apikey": key, "Accept": "application/json"}
        if target.type is TargetType.DOMAIN:
            path = f"domains/{target.value}"
        else:
            path = f"ip_addresses/{target.value}"
        data: Any = await self.get_json(f"{_BASE}/{path}", headers=headers)
        if not isinstance(data, dict):
            return []
        wrapper = data.get("data")
        if not isinstance(wrapper, dict):
            return []
        attrs = wrapper.get("attributes")
        if not isinstance(attrs, dict):
            return []
        findings: list[Finding] = []
        stats = attrs.get("last_analysis_stats")
        if isinstance(stats, dict):
            malicious = int(stats.get("malicious", 0) or 0)
            suspicious = int(stats.get("suspicious", 0) or 0)
            if malicious or suspicious:
                findings.append(
                    Finding(
                        source=self.name,
                        target=target.value,
                        confidence=Confidence.HIGH if malicious else Confidence.MEDIUM,
                        kind="analysis_stats",
                        value=f"malicious:{malicious},suspicious:{suspicious}",
                        normalized_data=dict(stats),
                        raw_evidence=Evidence(source_url=f"{_BASE}/{path}"),
                    )
                )
        if target.type is TargetType.DOMAIN:
            findings.extend(self._dns_records(target, attrs, path))
        else:
            findings.extend(self._resolutions(target, attrs, path))
        return findings

    def _dns_records(self, target: Target, attrs: dict[str, Any], path: str) -> list[Finding]:
        findings: list[Finding] = []
        seen: set[str] = set()
        for rec in attrs.get("last_dns_records", []):
            if not isinstance(rec, dict):
                continue
            rtype = str(rec.get("type", "")).upper()
            value = str(rec.get("value", "")).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            if rtype in {"A", "AAAA"}:
                kind = "resolution"
                node_type = "ip"
                node_id = value
            elif rtype == "CNAME":
                kind = "cname"
                node_type = "domain"
                node_id = value.rstrip(".")
            else:
                continue
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.MEDIUM,
                    kind=kind,
                    value=value,
                    normalized_data={"type": rtype, "ttl": rec.get("ttl")},
                    raw_evidence=Evidence(source_url=f"{_BASE}/{path}"),
                    graph_node_hint=GraphNodeHint(
                        node_type=node_type,
                        node_id=node_id,
                        label=node_id,
                        parent_id=target.value,
                    ),
                )
            )
        return findings

    def _resolutions(self, target: Target, attrs: dict[str, Any], path: str) -> list[Finding]:
        findings: list[Finding] = []
        seen: set[str] = set()
        for host in attrs.get("hostnames", []):
            if not isinstance(host, str):
                continue
            h = host.lower().rstrip(".")
            if not h or h in seen:
                continue
            seen.add(h)
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.MEDIUM,
                    kind="hostname",
                    value=h,
                    normalized_data={},
                    raw_evidence=Evidence(source_url=f"{_BASE}/{path}"),
                    graph_node_hint=GraphNodeHint(
                        node_type="domain",
                        node_id=h,
                        label=h,
                        parent_id=target.value,
                    ),
                )
            )
        return findings
