"""Automatic target type detection and normalization.

Detection is regex + library validation, ordered from the most specific
type to the most general. ``tldextract`` is configured to use its bundled
Public Suffix List snapshot (``suffix_list_urls=()``): no network, fully
deterministic — important for a passive tool and for reproducible tests.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

import tldextract

from globeye.core.models import Target, TargetType

_extract = tldextract.TLDExtract(suffix_list_urls=())

_ASN_RE = re.compile(r"^as[n]?\s*(\d{1,10})$", re.IGNORECASE)
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_CERT_RE = re.compile(r"^[A-Fa-f0-9]{40}$|^[A-Fa-f0-9]{64}$")
_USERNAME_RE = re.compile(r"^@?[A-Za-z0-9_][A-Za-z0-9_.\-]{1,38}$")
_PHONE_RE = re.compile(r"^\+?\d[\d\s().\-]{5,18}\d$")
_PERSON_TOKEN_RE = re.compile(r"^[^\W\d_]+(?:[.'\-][^\W\d_]+)*$", re.UNICODE)


class TargetDetectionError(ValueError):
    """Raised when the input cannot be classified into a target type."""


def _strip_url(value: str) -> str:
    if "://" in value:
        netloc = urlparse(value).netloc or urlparse(value).path
        return netloc.split("@")[-1].split(":")[0]
    return value


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def _is_cidr(value: str) -> bool:
    if "/" not in value:
        return False
    try:
        ipaddress.ip_network(value, strict=False)
    except ValueError:
        return False
    return True


def _is_domain(value: str) -> bool:
    ext = _extract(value)
    return bool(ext.domain and ext.suffix)


def _looks_like_person(value: str) -> bool:
    tokens = value.split()
    if not 2 <= len(tokens) <= 5:
        return False
    return all(_PERSON_TOKEN_RE.match(tok) for tok in tokens)


def detect(raw: str) -> Target:
    """Classify ``raw`` into a :class:`Target`. Raises on empty input."""
    value = raw.strip()
    if not value:
        raise TargetDetectionError("empty target")

    if _is_cidr(value):
        net = ipaddress.ip_network(value, strict=False)
        return Target(raw=raw, type=TargetType.CIDR, value=str(net))

    if _is_ip(value):
        return Target(raw=raw, type=TargetType.IP, value=str(ipaddress.ip_address(value)))

    if m := _ASN_RE.match(value):
        return Target(raw=raw, type=TargetType.ASN, value=f"AS{int(m.group(1))}")

    if _EMAIL_RE.match(value):
        return Target(raw=raw, type=TargetType.EMAIL, value=value.lower())

    if _CERT_RE.match(value):
        return Target(raw=raw, type=TargetType.CERT_HASH, value=value.lower())

    host = _strip_url(value)
    if _is_domain(host):
        return Target(raw=raw, type=TargetType.DOMAIN, value=host.lower().rstrip("."))

    digits = re.sub(r"\D", "", value)
    if _PHONE_RE.match(value) and 7 <= len(digits) <= 15:
        normalized = ("+" if value.lstrip().startswith("+") else "") + digits
        return Target(raw=raw, type=TargetType.PHONE, value=normalized)

    if " " not in value and _USERNAME_RE.match(value):
        return Target(raw=raw, type=TargetType.USERNAME, value=value.lstrip("@"))

    if _looks_like_person(value):
        return Target(raw=raw, type=TargetType.PERSON, value=value)

    return Target(raw=raw, type=TargetType.ORG, value=value)
