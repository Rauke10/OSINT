"""Wayback URL grouping by path patterns (Fase 2C.3)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

WaybackCategory = str
WaybackPriority = str

CATEGORIES: tuple[str, ...] = (
    "admin_login",
    "api_endpoint",
    "backup_archive",
    "document",
    "upload",
    "wordpress",
    "static_asset",
    "parameterized_url",
    "other",
)

PRIORITIES: tuple[str, ...] = ("high", "medium", "low", "noisy")

_HIGH_PATH = re.compile(
    r"(/admin\b|/login\b|/wp-admin|/wp-login|/graphql\b|/api\b|\.env\b|\.bak\b|"
    r"\.sql\b|\.zip\b|\.tar\b|\.gz\b|\.backup\b)",
    re.I,
)
_WP = re.compile(r"(/wp-admin|/wp-login|wp-content|wordpress)", re.I)
_API = re.compile(r"(/api\b|/graphql\b|/v\d+/|/rest/)", re.I)
_BACKUP = re.compile(r"\.(bak|sql|zip|tar|gz|backup|old|dump)\b", re.I)
_DOC = re.compile(r"\.(pdf|docx?|xlsx?|pptx?|odt)\b", re.I)
_UPLOAD = re.compile(r"(/uploads?/|/files/|/documents/)", re.I)
_STATIC = re.compile(
    r"\.(css|js|mjs|png|jpe?g|gif|svg|webp|ico|woff2?|ttf|map)\b|"
    r"(/static/|/assets/|/thumbnails?/|tracking|cache[_-]?bust)",
    re.I,
)
_QUERY_BUST = re.compile(r"[?&](v|ver|version|cache|_=)\d", re.I)


@dataclass(frozen=True, slots=True)
class UrlGroupMeta:
    host: str
    path_base: str
    extension: str
    category: WaybackCategory
    priority: WaybackPriority
    group_key: str


def _path_of(url: str) -> str:
    try:
        return urlparse(url if "://" in url else f"https://{url}").path or "/"
    except Exception:
        return "/"


def _extension(path: str) -> str:
    base = path.split("?")[0].split("#")[0]
    if "." not in base.rstrip("/").split("/")[-1]:
        return ""
    return base.rsplit(".", 1)[-1].lower()


def classify_wayback_url(url: str) -> UrlGroupMeta:
    """Classify a URL for Wayback explorer grouping."""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or "").lower()
    path = parsed.path or "/"
    ext = _extension(path)
    path_lower = path.lower()

    category: WaybackCategory = "other"
    priority: WaybackPriority = "low"

    if _BACKUP.search(path_lower):
        category, priority = "backup_archive", "high"
    elif _WP.search(path_lower):
        category, priority = "wordpress", "high"
    elif _HIGH_PATH.search(path_lower) or path_lower.endswith("/.env"):
        if _API.search(path_lower):
            category, priority = "api_endpoint", "high"
        elif "/login" in path_lower or "/admin" in path_lower:
            category, priority = "admin_login", "high"
        else:
            category, priority = "admin_login", "high"
    elif _API.search(path_lower):
        category, priority = "api_endpoint", "high"
    elif _DOC.search(path_lower):
        category, priority = "document", "medium"
    elif _UPLOAD.search(path_lower):
        if ext in {"jpg", "jpeg", "png", "gif", "svg", "webp"}:
            category, priority = "static_asset", "noisy"
        else:
            category, priority = "upload", "medium"
    elif _STATIC.search(path_lower) or ext in {
        "css",
        "js",
        "png",
        "jpg",
        "jpeg",
        "svg",
        "gif",
        "woff",
        "woff2",
    }:
        category, priority = "static_asset", "noisy"
    elif "?" in url and _QUERY_BUST.search(url):
        category, priority = "parameterized_url", "noisy"
    elif ext in {"", "html", "htm", "php", "asp", "aspx"}:
        category, priority = "other", "low"
    else:
        category, priority = "other", "low"

    parts = [p for p in path_lower.split("/") if p]
    path_base = "/" + parts[0] if parts else "/"
    if category in {"admin_login", "api_endpoint", "wordpress"} and len(parts) >= 2:
        path_base = f"/{parts[0]}/{parts[1]}"

    group_key = f"{host}|{category}|{path_base}"
    return UrlGroupMeta(
        host=host,
        path_base=path_base,
        extension=ext,
        category=category,
        priority=priority,
        group_key=group_key,
    )


_GROUP_REASONS: dict[str, str] = {
    "admin_login": "Ruta sensible de login/admin detectada por patrón",
    "api_endpoint": "Endpoint de API o GraphQL detectado por patrón",
    "backup_archive": "Archivo de copia o respaldo por extensión",
    "document": "Documento (PDF, Office, etc.) por extensión",
    "upload": "Ruta de subida o ficheros (/uploads, /files, /documents)",
    "wordpress": "Ruta WordPress (wp-admin, wp-login, wp-content)",
    "static_asset": "Recurso estático (CSS, JS, imagen, fuente)",
    "parameterized_url": "URL con parámetros de caché/versión",
    "other": "Otras rutas archivadas",
}


def wayback_group_reason(meta: UrlGroupMeta) -> str:
    """Human-readable non-destructive grouping explanation."""
    base = _GROUP_REASONS.get(meta.category, _GROUP_REASONS["other"])
    return f"{base} (prefijo {meta.path_base})"


def wayback_group_summary(items: list[dict[str, object]]) -> dict[str, dict[str, int]]:
    """Aggregate counts per category from explorer items (Wayback URLs only)."""
    summary: dict[str, dict[str, int]] = {}
    for it in items:
        if not it.get("is_wayback_url"):
            continue
        cat = str(it.get("wayback_category") or "other")
        bucket = summary.setdefault(
            cat,
            {
                "total": 0,
                "visible": 0,
                "live": 0,
                "unchecked": 0,
                "not_found": 0,
                "discarded": 0,
            },
        )
        bucket["total"] += 1
        if not it.get("hidden"):
            bucket["visible"] += 1
        if it.get("hidden") or it.get("review_status") == "discarded":
            bucket["discarded"] += 1
        ls = str(it.get("live_status") or "not_checked")
        if ls == "live_200" or ls == "redirect":
            bucket["live"] += 1
        elif ls == "not_checked":
            bucket["unchecked"] += 1
        elif ls == "not_found":
            bucket["not_found"] += 1
    return summary
