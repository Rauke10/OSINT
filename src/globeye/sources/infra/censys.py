"""Censys — hosts & certificates already indexed by Censys (passive)."""

from __future__ import annotations

import base64
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

_BASE = "https://search.censys.io/api/v2"


@register
class CensysSource(PassiveSource):
    """Censys Search v2 (host view + certificate name search)."""

    name: ClassVar[str] = "censys"
    requires_api_key: ClassVar[bool] = True
    supported_target_types: ClassVar[set[TargetType]] = {
        TargetType.IP,
        TargetType.DOMAIN,
    }
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=2, per=5, concurrency=1)
    allowed_hosts: ClassVar[set[str]] = {"search.censys.io"}

    def _creds(self) -> tuple[str, str] | None:
        cid = self.ctx.settings.censys_api_id
        secret = self.ctx.settings.censys_api_secret
        if cid and secret:
            return cid.get_secret_value(), secret.get_secret_value()
        return None

    def available(self) -> bool:
        return self._creds() is not None

    def api_key(self) -> str | None:
        creds = self._creds()
        return creds[0] if creds else None

    def _auth_header(self) -> dict[str, str]:
        creds = self._creds()
        if not creds:
            return {}
        token = base64.b64encode(f"{creds[0]}:{creds[1]}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    async def fetch(self, target: Target) -> list[Finding]:
        if not self.available():
            return []
        headers = self._auth_header()
        if target.type is TargetType.IP:
            return await self._host(target, headers)
        return await self._certs(target, headers)

    async def _host(self, target: Target, headers: dict[str, str]) -> list[Finding]:
        data: Any = await self.get_json(f"{_BASE}/hosts/{target.value}", headers=headers)
        result = data.get("result", {}) if isinstance(data, dict) else {}
        findings: list[Finding] = []
        for svc in result.get("services", []):
            if not isinstance(svc, dict):
                continue
            proto = svc.get("transport_protocol", "TCP")
            findings.append(
                Finding(
                    source=self.name,
                    target=target.value,
                    confidence=Confidence.HIGH,
                    kind="service",
                    value=f"{target.value}:{svc.get('port')}/{proto}",
                    normalized_data={
                        "service_name": svc.get("service_name"),
                        "port": svc.get("port"),
                    },
                    raw_evidence=Evidence(source_url=f"{_BASE}/hosts/{target.value}"),
                )
            )
        return findings

    async def _certs(self, target: Target, headers: dict[str, str]) -> list[Finding]:
        data: Any = await self.get_json(
            f"{_BASE}/certificates/search",
            params={"q": f"names: {target.value}", "per_page": "50"},
            headers=headers,
        )
        hits = data.get("result", {}).get("hits", []) if isinstance(data, dict) else []
        seen: set[str] = set()
        findings: list[Finding] = []
        for hit in hits:
            for name in hit.get("names", []) if isinstance(hit, dict) else []:
                sub = str(name).lower().lstrip("*.").rstrip(".")
                if not sub or sub in seen:
                    continue
                if sub != target.value and not sub.endswith("." + target.value):
                    continue
                seen.add(sub)
                findings.append(
                    Finding(
                        source=self.name,
                        target=target.value,
                        confidence=Confidence.MEDIUM,
                        kind="subdomain",
                        value=sub,
                        raw_evidence=Evidence(source_url=f"{_BASE}/certificates/search"),
                        graph_node_hint=GraphNodeHint(
                            node_type="domain",
                            node_id=sub,
                            label=sub,
                            parent_id=target.value,
                        ),
                    )
                )
        return findings
