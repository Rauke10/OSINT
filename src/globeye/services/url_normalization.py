"""Safe URL normalization for entities (Fase 2C.4).

Distinct paths, files, endpoints and hosts are never merged. Only safe transforms:
lowercase host, optional trailing-slash removal on non-file paths, tracking-param stripping
with originals preserved elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_EXACT = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "ref",
        "_ga",
    }
)


def _is_tracking_param(name: str) -> bool:
    n = name.lower()
    if n in TRACKING_EXACT:
        return True
    return n.startswith("utm_")


def _path_has_file_extension(path: str) -> bool:
    segment = path.rstrip("/").split("/")[-1] if path else ""
    if not segment or segment in {".", ".."}:
        return False
    return "." in segment and not segment.startswith(".")


def _strip_trailing_slash(path: str) -> str:
    if not path or path == "/":
        return path or "/"
    if _path_has_file_extension(path):
        return path
    return path.rstrip("/") or "/"


@dataclass(frozen=True, slots=True)
class UrlNormalizationResult:
    original_value: str
    normalized_value: str
    canonical_key: str
    display_value: str
    normalization_reason: str
    is_normalized_variant: bool
    stripped_tracking_params: tuple[str, ...]


def _parse(url: str) -> tuple[str, str, str, str, str, str]:
    """Return (scheme, netloc, path, params, query, fragment) with default scheme."""
    raw = url.strip()
    if not raw:
        return "", "", "/", "", "", ""
    if "://" not in raw:
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.netloc or "").lower()
    path = parsed.path or "/"
    return scheme, host, path, parsed.params, parsed.query, parsed.fragment


def normalize_url_for_entity(url: str) -> UrlNormalizationResult:
    """Build entity identity key and canonical equivalence key for a URL."""
    original = url.strip()
    scheme, host, path, params, query, _fragment = _parse(original)
    reasons: list[str] = []
    stripped: list[str] = []

    if host != (urlparse(original if "://" in original else f"https://{original}").netloc or ""):
        reasons.append("host en minúsculas")

    path_norm = _strip_trailing_slash(path)
    if path_norm != path:
        reasons.append("barra final eliminada (ruta no es archivo)")

    query_pairs = parse_qsl(query, keep_blank_values=True)
    kept: list[tuple[str, str]] = []
    for k, v in query_pairs:
        if _is_tracking_param(k):
            stripped.append(k)
        else:
            kept.append((k, v))
    query_norm = urlencode(kept, doseq=True)
    if stripped:
        reasons.append(f"parámetros de tracking omitidos en clave: {', '.join(stripped)}")

    normalized = urlunparse((scheme, host, path_norm, params, query_norm, ""))
    canonical_scheme = "https"
    canonical = urlunparse((canonical_scheme, host, path_norm, params, query_norm, ""))

    if not reasons:
        reason = "Sin cambios destructivos; se conserva path, archivo y endpoint"
    else:
        reason = "; ".join(reasons)

    return UrlNormalizationResult(
        original_value=original,
        normalized_value=normalized,
        canonical_key=canonical,
        display_value=original[:512],
        normalization_reason=reason,
        is_normalized_variant=bool(stripped)
        or path_norm != path
        or host != urlparse(original if "://" in original else f"https://{original}").netloc,
        stripped_tracking_params=tuple(stripped),
    )


def urls_are_equivalent(a: str, b: str) -> bool:
    """True only when two URLs are the same resource (login vs login/, http/https)."""
    return normalize_url_for_entity(a).canonical_key == normalize_url_for_entity(b).canonical_key


def urls_must_remain_distinct(a: str, b: str) -> bool:
    """True when paths/resources differ and must not be merged."""
    na = normalize_url_for_entity(a)
    nb = normalize_url_for_entity(b)
    if na.normalized_value == nb.normalized_value:
        return False
    return na.canonical_key != nb.canonical_key
