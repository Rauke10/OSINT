"""Normalize source failures into short, UI-friendly skip reasons."""

from __future__ import annotations

import httpx

from globeye.config import ProxyConfigError


def skip_reason_to_status(reason: str) -> str:
    """Map orchestrator skip text to a stable ``SourceResult.status`` value."""
    lower = reason.lower()
    if "missing api key" in lower or "sin clave" in lower:
        return "missing_key"
    if (
        "invalid api key" in lower
        or "inválida" in lower
        or "no autorizada" in lower
        or "sin permisos" in lower
    ):
        return "invalid_key"
    if "rate limit" in lower or "cuota" in lower or "límite" in lower:
        return "rate_limited"
    if "proxy" in lower or "configuration error" in lower or "configuración" in lower:
        return "config_error"
    if "timeout" in lower:
        return "timeout"
    if "network" in lower or "proveedor" in lower:
        return "network_error"
    if "endpoint incompatible" in lower or "api distinta" in lower:
        return "failed"
    return "failed"


def error_type_from_reason(reason: str | None) -> str | None:
    if not reason:
        return None
    status = skip_reason_to_status(reason)
    return None if status in {"used", "no_results"} else status


def format_source_error(exc: BaseException) -> str:
    """Map an exception from ``source.fetch()`` to a stable skip reason."""
    if isinstance(exc, RuntimeError) and exc.__cause__ is not None:
        return format_source_error(exc.__cause__)
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 401:
            return "API key inválida o no autorizada"
        if code == 403:
            return "API key válida, pero sin permisos/cuota para este endpoint"
        if code == 429:
            return "Límite de cuota alcanzado"
        if code >= 500:
            return "Error temporal del proveedor"
        if code == 404:
            return "Sin datos en el proveedor (404)"
        body = ""
        try:
            body = str(exc.response.text)[:200].lower()
        except Exception:
            body = ""
        if "endpoint" in body or "not found" in body:
            return "El proveedor parece usar una API distinta a la esperada"
        return f"HTTP {code} del proveedor"
    if isinstance(exc, httpx.TimeoutException):
        return "Timeout de red"
    if isinstance(exc, httpx.TransportError):
        return "Timeout de red"
    if isinstance(exc, ProxyConfigError):
        return "proxy configuration error"
    msg = str(exc).lower()
    if "proxy" in msg or "unknown scheme" in msg:
        return "proxy configuration error"
    if "timeout" in msg:
        return "network timeout"
    return f"error: {type(exc).__name__}"
