"""RDAP — registration data for domains, IPs and ASNs.

Passive: RDAP servers are the *registry's* third-party servers (RIRs /
registries) that already hold this data. We never contact the target; the
allowlist is the set of well-known RDAP endpoints (rdap.org bootstrap +
the RIRs/registries it redirects to).
"""

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

_BASE = "https://rdap.org"
_PATH = {
    TargetType.DOMAIN: "domain",
    TargetType.IP: "ip",
    TargetType.ASN: "autnum",
}


def _entities(data: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stack = list(data.get("entities", []))
    while stack:
        ent = stack.pop()
        if isinstance(ent, dict):
            out.append(ent)
            stack.extend(ent.get("entities", []))
    return out


def _vcard_email(entity: dict[str, Any]) -> str | None:
    vcard = entity.get("vcardArray")
    if not isinstance(vcard, list) or len(vcard) < 2:
        return None
    for field in vcard[1]:
        if isinstance(field, list) and field and field[0] == "email":
            return str(field[3]) if len(field) > 3 else None
    return None


@register
class RdapSource(PassiveSource):
    """Registration Data Access Protocol lookup."""

    name: ClassVar[str] = "rdap"
    requires_api_key: ClassVar[bool] = False
    supported_target_types: ClassVar[set[TargetType]] = {
        TargetType.DOMAIN,
        TargetType.IP,
        TargetType.ASN,
    }
    rate_limit: ClassVar[RateLimit] = RateLimit(rate=1, per=1, concurrency=2)
    allowed_hosts: ClassVar[set[str]] = {
        "rdap.org",
        "rdap.arin.net",
        "rdap.db.ripe.net",
        "rdap.apnic.net",
        "rdap.lacnic.net",
        "rdap.afrinic.net",
        "rdap.verisign.com",
        "rdap.markmonitor.com",
        "rdap.publicinterestregistry.org",
        "rdap.identitydigital.services",
        "rdap.centralnic.com",
        "rdap.nic.google",
    }

    async def fetch(self, target: Target) -> list[Finding]:
        path = _PATH[target.type]
        value = target.value.removeprefix("AS") if target.type is TargetType.ASN else target.value
        data: Any = await self.get_json(f"{_BASE}/{path}/{value}")
        if not isinstance(data, dict):
            return []

        url = f"{_BASE}/{path}/{value}"
        findings: list[Finding] = [
            Finding(
                source=self.name,
                target=target.value,
                confidence=Confidence.HIGH,
                kind="registration",
                value=str(data.get("handle") or data.get("ldhName") or target.value),
                normalized_data={
                    "name": data.get("name"),
                    "status": data.get("status"),
                    "events": data.get("events"),
                    "nameservers": [
                        ns.get("ldhName")
                        for ns in data.get("nameservers", [])
                        if isinstance(ns, dict)
                    ],
                },
                raw_evidence=Evidence(
                    source_url=url,
                    raw={"objectClassName": data.get("objectClassName")},
                ),
            )
        ]

        for ent in _entities(data):
            roles = ent.get("roles", [])
            email = _vcard_email(ent)
            if email:
                findings.append(
                    Finding(
                        source=self.name,
                        target=target.value,
                        confidence=Confidence.MEDIUM,
                        kind="contact_email",
                        value=email.lower(),
                        normalized_data={"roles": roles, "handle": ent.get("handle")},
                        raw_evidence=Evidence(source_url=url),
                        graph_node_hint=GraphNodeHint(
                            node_type="email",
                            node_id=email.lower(),
                            label=email.lower(),
                            parent_id=target.value,
                        ),
                        pivot_target=Target(raw=email, type=TargetType.EMAIL, value=email.lower()),
                    )
                )
        return findings
