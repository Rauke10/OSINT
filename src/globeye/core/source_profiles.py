"""Centralized source routing profiles by target type and scan depth (Fase 2B)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from globeye.core.models import TargetType

# Re-export for callers
__all__ = [
    "SOURCE_SPECS",
    "CostLevel",
    "ScanDepth",
    "profile_id_for",
    "profile_source_names",
    "reason_not_applicable",
    "source_spec",
    "special_target_warning",
]


class ScanDepth(StrEnum):
    """How aggressively passive sources are consulted."""

    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class CostLevel(StrEnum):
    FREE = "free"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class SourceSpec:
    """Metadata for routing, cost estimation and future settings UI."""

    cost_level: CostLevel
    depth_levels: frozenset[ScanDepth]
    requires_key: bool
    supported_targets: frozenset[TargetType]
    enabled: bool = True
    run_reason: str = ""


SOURCE_SPECS: dict[str, SourceSpec] = {
    "rdap": SourceSpec(
        CostLevel.FREE,
        frozenset({ScanDepth.QUICK, ScanDepth.STANDARD, ScanDepth.DEEP}),
        False,
        frozenset({TargetType.DOMAIN, TargetType.IP, TargetType.ASN}),
        run_reason="Registration data (RDAP/WHOIS)",
    ),
    "crtsh": SourceSpec(
        CostLevel.FREE,
        frozenset({ScanDepth.QUICK, ScanDepth.STANDARD, ScanDepth.DEEP}),
        False,
        frozenset({TargetType.DOMAIN}),
        run_reason="Certificate Transparency subdomains",
    ),
    "wayback": SourceSpec(
        CostLevel.FREE,
        frozenset({ScanDepth.QUICK, ScanDepth.STANDARD, ScanDepth.DEEP}),
        False,
        frozenset({TargetType.DOMAIN}),
        run_reason="Archived URLs (Wayback CDX)",
    ),
    "securitytrails": SourceSpec(
        CostLevel.MEDIUM,
        frozenset({ScanDepth.STANDARD, ScanDepth.DEEP}),
        True,
        frozenset({TargetType.DOMAIN}),
        run_reason="Passive DNS and subdomains",
    ),
    "censys": SourceSpec(
        CostLevel.MEDIUM,
        frozenset({ScanDepth.STANDARD, ScanDepth.DEEP}),
        True,
        frozenset({TargetType.IP, TargetType.DOMAIN}),
        run_reason="Indexed hosts and certificates",
    ),
    "shodan": SourceSpec(
        CostLevel.MEDIUM,
        frozenset({ScanDepth.STANDARD, ScanDepth.DEEP}),
        True,
        frozenset({TargetType.IP, TargetType.DOMAIN}),
        run_reason="Indexed services and DNS",
    ),
    "virustotal": SourceSpec(
        CostLevel.LOW,
        frozenset({ScanDepth.STANDARD, ScanDepth.DEEP}),
        True,
        frozenset({TargetType.DOMAIN, TargetType.IP}),
        run_reason="Passive DNS and analysis metadata",
    ),
    "otx": SourceSpec(
        CostLevel.LOW,
        frozenset({ScanDepth.STANDARD, ScanDepth.DEEP}),
        True,
        frozenset({TargetType.DOMAIN, TargetType.IP}),
        run_reason="AlienVault OTX passive DNS",
    ),
    "hunter": SourceSpec(
        CostLevel.MEDIUM,
        frozenset({ScanDepth.STANDARD, ScanDepth.DEEP}),
        True,
        frozenset({TargetType.DOMAIN}),
        run_reason="Known emails for a domain",
    ),
    "hibp": SourceSpec(
        CostLevel.MEDIUM,
        frozenset({ScanDepth.STANDARD, ScanDepth.DEEP}),
        True,
        frozenset({TargetType.EMAIL}),
        run_reason="Breach membership (metadata only)",
    ),
    "dehashed": SourceSpec(
        CostLevel.HIGH,
        frozenset({ScanDepth.DEEP}),
        True,
        frozenset({TargetType.EMAIL, TargetType.USERNAME}),
        run_reason="Breach metadata (deep; no credentials stored)",
    ),
    "gravatar": SourceSpec(
        CostLevel.FREE,
        frozenset({ScanDepth.QUICK, ScanDepth.STANDARD, ScanDepth.DEEP}),
        False,
        frozenset({TargetType.EMAIL}),
        run_reason="Public profile from email hash",
    ),
    "github": SourceSpec(
        CostLevel.HIGH,
        frozenset({ScanDepth.DEEP}),
        True,
        frozenset({TargetType.DOMAIN, TargetType.EMAIL, TargetType.ORG}),
        run_reason="Public code search (quota-intensive)",
    ),
    "pastebin": SourceSpec(
        CostLevel.HIGH,
        frozenset({ScanDepth.DEEP}),
        True,
        frozenset({TargetType.DOMAIN, TargetType.EMAIL}),
        run_reason="Public pastes via search index",
    ),
    "username_enum": SourceSpec(
        CostLevel.FREE,
        frozenset({ScanDepth.QUICK, ScanDepth.STANDARD, ScanDepth.DEEP}),
        False,
        frozenset({TargetType.USERNAME}),
        run_reason="Public profile presence checks",
    ),
    "abuseipdb": SourceSpec(
        CostLevel.LOW,
        frozenset({ScanDepth.STANDARD, ScanDepth.DEEP}),
        True,
        frozenset({TargetType.IP}),
        run_reason="IP abuse reports",
    ),
}

# Target-type profiles: (profile_id, ordered source names)
_TARGET_PROFILES: dict[TargetType, tuple[str, tuple[str, ...]]] = {
    TargetType.DOMAIN: (
        "domain_passive_intel",
        (
            "rdap",
            "crtsh",
            "securitytrails",
            "censys",
            "shodan",
            "virustotal",
            "otx",
            "wayback",
            "hunter",
            "github",
            "pastebin",
        ),
    ),
    TargetType.IP: (
        "ip_reputation_infrastructure",
        (
            "rdap",
            "shodan",
            "censys",
            "virustotal",
            "abuseipdb",
            "otx",
        ),
    ),
    TargetType.EMAIL: (
        "email_identity_breach",
        (
            "hibp",
            "hunter",
            "dehashed",
            "gravatar",
            "github",
            "pastebin",
        ),
    ),
    TargetType.USERNAME: (
        "username_social",
        ("username_enum", "github", "dehashed", "pastebin"),
    ),
    TargetType.PHONE: ("phone_lookup", ()),
    TargetType.PERSON: ("person_sensitive", ()),
    TargetType.ORG: ("organization_public", ("github",)),
    TargetType.ASN: (
        "asn_infrastructure",
        ("rdap", "shodan", "censys"),
    ),
    TargetType.CIDR: ("cidr_limited", ()),
    TargetType.CERT_HASH: (
        "cert_fingerprint",
        ("censys", "virustotal", "crtsh"),
    ),
}

# Human-readable exclusion reasons (profile vs. technical capability)
_TYPE_MISMATCH: dict[tuple[TargetType, str], str] = {
    (TargetType.IP, "hunter"): "Hunter applies to domains/emails, not IPs",
    (TargetType.IP, "hibp"): "Have I Been Pwned applies to emails only",
    (TargetType.IP, "gravatar"): "Gravatar applies to emails only",
    (TargetType.IP, "crtsh"): "crt.sh applies to domains, not IPs",
    (TargetType.IP, "wayback"): "Wayback applies to domains, not IPs",
    (TargetType.IP, "securitytrails"): "SecurityTrails applies to domains only",
    (TargetType.IP, "username_enum"): "Username enumeration applies to usernames only",
    (TargetType.DOMAIN, "abuseipdb"): "AbuseIPDB applies to IPs only",
    (TargetType.DOMAIN, "hibp"): "Have I Been Pwned applies to emails only",
    (TargetType.EMAIL, "hunter"): "Hunter looks up domain emails, not mailbox-only queries",
    (TargetType.EMAIL, "crtsh"): "crt.sh applies to domains, not raw emails",
    (TargetType.EMAIL, "shodan"): "Shodan applies to IPs and domains, not emails",
    (TargetType.EMAIL, "abuseipdb"): "AbuseIPDB applies to IPs only",
    (TargetType.USERNAME, "hibp"): "Have I Been Pwned applies to emails only",
    (TargetType.USERNAME, "hunter"): "Hunter applies to domains, not usernames",
    (TargetType.CERT_HASH, "crtsh"): "crt.sh searches by domain name, not certificate hash",
    (TargetType.CERT_HASH, "rdap"): "RDAP applies to domains, IPs and ASNs, not cert hashes",
    (TargetType.CERT_HASH, "abuseipdb"): "AbuseIPDB applies to IPs only",
    (TargetType.ASN, "abuseipdb"): "AbuseIPDB applies to IPs, not ASNs",
    (TargetType.ASN, "crtsh"): "crt.sh applies to domains, not ASNs",
    (TargetType.ASN, "virustotal"): "VirusTotal host lookup does not apply to ASN identifiers",
    (TargetType.ORG, "shodan"): "Shodan applies to IPs and domains, not organization names",
    (TargetType.ORG, "rdap"): "RDAP applies to domains, IPs and ASNs, not free-text org names",
}

_PROFILE_EXCLUDED: dict[tuple[TargetType, str], str] = {
    (TargetType.IP, "github"): "GitHub code search is not in the IP profile",
    (TargetType.IP, "pastebin"): "Pastebin search is not in the IP profile",
    (TargetType.IP, "dehashed"): "DeHashed is not in the IP profile",
    (TargetType.DOMAIN, "username_enum"): "Username enumeration is not in the domain profile",
    (TargetType.EMAIL, "rdap"): "RDAP is not in the email profile",
}


def profile_id_for(target_type: TargetType) -> str:
    return _TARGET_PROFILES[target_type][0]


def profile_source_names(target_type: TargetType, depth: ScanDepth) -> list[str]:
    """Sources selected by target profile and scan depth."""
    _, names = _TARGET_PROFILES[target_type]
    out: list[str] = []
    for name in names:
        spec = SOURCE_SPECS.get(name)
        if spec is None or not spec.enabled:
            continue
        if depth not in spec.depth_levels:
            continue
        out.append(name)
    return out


def source_spec(name: str) -> SourceSpec | None:
    return SOURCE_SPECS.get(name)


def reason_not_applicable(target_type: TargetType, source_name: str) -> str:
    key = (target_type, source_name)
    if key in _TYPE_MISMATCH:
        return _TYPE_MISMATCH[key]
    if key in _PROFILE_EXCLUDED:
        return _PROFILE_EXCLUDED[key]
    spec = SOURCE_SPECS.get(source_name)
    if spec and target_type not in spec.supported_targets:
        supported = ", ".join(sorted(t.value for t in spec.supported_targets))
        return f"{source_name} supports {supported}, not {target_type.value}"
    return f"{source_name} is not in the {profile_id_for(target_type)} profile"


def special_target_warning(target_type: TargetType) -> str | None:
    if target_type is TargetType.PHONE:
        return "No hay fuentes de teléfono configuradas todavía."
    if target_type is TargetType.PERSON:
        return (
            "Tipo sensible: requiere justificación y fuentes específicas no implementadas todavía."
        )
    if target_type is TargetType.CIDR:
        return "CIDR detectado, pero el escaneo masivo no está habilitado en Fase 2B."
    return None
