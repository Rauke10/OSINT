"""Manual active URL live checks (Fase 2C.2).

Contacts target URLs directly on analyst request only — not part of passive scan.
"""

from __future__ import annotations

import asyncio
import re
import time
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

from globeye.config import Settings
from globeye.db.models import Entity, UrlLiveCheck
from globeye.utils.redact import Redactor

LiveStatus = Literal[
    "not_checked",
    "live_200",
    "redirect",
    "forbidden",
    "not_found",
    "server_error",
    "timeout",
    "network_error",
    "invalid_url",
]

MAX_BATCH_URLS = 25
CHECK_TIMEOUT_SECONDS = 5.0
MAX_REDIRECTS = 3
RATE_LIMIT_DELAY_SECONDS = 0.25

_SECRET_IN_URL = re.compile(
    r"(?i)([?&](?:api[_-]?key|token|secret|password|passwd|auth)=)([^&\s#]+)"
)


def redact_url_for_storage(url: str, settings: Settings) -> str:
    """Strip obvious secrets from query strings before persisting."""

    def _sub(match: re.Match[str]) -> str:
        return f"{match.group(1)}{Redactor().scrub(match.group(2))}"

    redacted = _SECRET_IN_URL.sub(_sub, url)
    for secret in settings.secret_values():
        if secret and secret in redacted:
            redacted = redacted.replace(secret, "****")
    return redacted[:2048]


_WEB_CHECKABLE_TYPES = frozenset({"url", "archived_url", "domain", "subdomain"})


def url_for_entity_check(entity_type: str, display_value: str, normalized_value: str) -> str:
    """Build probe URL: exact URL for url types; https://host for domain/subdomain."""
    raw = (display_value or normalized_value).strip()
    et = entity_type.lower()
    if et in {"url", "archived_url"}:
        return raw
    if et in {"domain", "subdomain", "registration"}:
        host = raw.split("/")[0].split("?")[0]
        return f"https://{host}"
    return raw


def normalize_check_url(raw: str) -> str | None:
    """Return a normalized http(s) URL or None if invalid."""
    text = raw.strip()
    if not text:
        return None
    if "://" not in text:
        text = f"https://{text}"
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"}:
        return None
    if not parsed.netloc:
        return None
    return text


def status_from_response(status_code: int) -> LiveStatus:
    if status_code == 200 or (200 < status_code < 300):
        return "live_200"
    if status_code in {301, 302, 303, 307, 308}:
        return "redirect"
    if status_code in {401, 403}:
        return "forbidden"
    if status_code == 404:
        return "not_found"
    if status_code >= 500:
        return "server_error"
    return "forbidden"


def _build_live_client(settings: Settings) -> httpx.AsyncClient:
    """Client for direct target URL checks (no passive host allowlist)."""
    ua = settings.user_agent
    if "globeye" not in ua.lower():
        ua = f"GLOBEYE-URL-Check/0.1 ({ua})"
    return httpx.AsyncClient(
        timeout=CHECK_TIMEOUT_SECONDS,
        headers={"User-Agent": ua, "Accept": "*/*"},
        proxy=settings.proxy_url or None,
        follow_redirects=False,
    )


async def probe_url(
    url: str,
    settings: Settings,
    *,
    method: str = "HEAD",
    fallback_get: bool = True,
    fallback_http: bool = False,
) -> dict[str, Any]:
    """Perform one live check; returns fields for UrlLiveCheck (no DB write)."""
    normalized = normalize_check_url(url)
    if normalized is None:
        return {
            "url": redact_url_for_storage(url, settings),
            "method": method.upper(),
            "status": "invalid_url",
            "status_code": None,
            "final_url": None,
            "content_type": None,
            "content_length": None,
            "checked_at": datetime.now(UTC),
            "latency_ms": None,
            "error_message": "URL inválida (solo http/https)",
        }

    safe_url = redact_url_for_storage(normalized, settings)
    req_method = method.upper()
    if req_method not in {"HEAD", "GET"}:
        req_method = "HEAD"

    started = time.perf_counter()
    async with _build_live_client(settings) as client:
        try:
            result = await _request_once(client, safe_url, method=req_method)
            if fallback_get and req_method == "HEAD" and result.get("status_code") == 405:
                result = await _request_once(client, safe_url, method="GET")
                result["method"] = "GET"
            else:
                result["method"] = req_method
            if (
                fallback_http
                and safe_url.startswith("https://")
                and result.get("status")
                in {
                    "network_error",
                    "timeout",
                }
            ):
                http_url = redact_url_for_storage(
                    safe_url.replace("https://", "http://", 1), settings
                )
                http_result = await _request_once(client, http_url, method=req_method)
                if http_result.get("status") not in {"network_error", "timeout"}:
                    http_result["method"] = req_method
                    result = http_result
        except httpx.TimeoutException:
            elapsed = int((time.perf_counter() - started) * 1000)
            return _error_row(
                safe_url,
                req_method,
                status="timeout",
                error_message="Timeout de red",
                latency_ms=elapsed,
            )
        except httpx.TransportError as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            return _error_row(
                safe_url,
                req_method,
                status="network_error",
                error_message=f"Error de red: {type(exc).__name__}",
                latency_ms=elapsed,
            )
        except Exception as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            return _error_row(
                safe_url,
                req_method,
                status="network_error",
                error_message=str(exc)[:512],
                latency_ms=elapsed,
            )

    elapsed = int((time.perf_counter() - started) * 1000)
    result["latency_ms"] = elapsed
    result["url"] = safe_url
    result["checked_at"] = datetime.now(UTC)
    return result


async def _request_once(client: httpx.AsyncClient, url: str, *, method: str) -> dict[str, Any]:
    resp = await client.request(method, url)
    code = resp.status_code
    status = status_from_response(code)
    clen = resp.headers.get("content-length")
    try:
        content_length = int(clen) if clen is not None else None
    except ValueError:
        content_length = None
    return {
        "status": status,
        "status_code": code,
        "final_url": str(resp.url)[:2048],
        "content_type": (resp.headers.get("content-type") or "")[:256] or None,
        "content_length": content_length,
        "error_message": None,
    }


def _error_row(
    url: str,
    method: str,
    *,
    status: LiveStatus,
    error_message: str,
    latency_ms: int | None,
) -> dict[str, Any]:
    return {
        "url": url,
        "method": method,
        "status": status,
        "status_code": None,
        "final_url": None,
        "content_type": None,
        "content_length": None,
        "checked_at": datetime.now(UTC),
        "latency_ms": latency_ms,
        "error_message": error_message,
    }


def _row_to_dict(row: UrlLiveCheck) -> dict[str, Any]:
    return {
        "id": int(row.id or 0),
        "case_id": row.case_id,
        "entity_id": row.entity_id,
        "evidence_id": row.evidence_id,
        "url": row.url,
        "method": row.method,
        "status": row.status,
        "status_code": row.status_code,
        "final_url": row.final_url,
        "content_type": row.content_type,
        "content_length": row.content_length,
        "checked_at": row.checked_at.isoformat() if row.checked_at else None,
        "latency_ms": row.latency_ms,
        "error_message": row.error_message,
        "created_at": row.created_at.isoformat(),
    }


async def run_url_checks(
    engine: Engine,
    settings: Settings,
    case_id: int,
    entries: list[dict[str, Any]],
    *,
    method: str = "HEAD",
    fallback_get: bool = True,
    fallback_http: bool = True,
    max_urls: int = MAX_BATCH_URLS,
) -> dict[str, Any]:
    """Check up to ``max_urls`` URLs and persist results."""
    cap = min(max(max_urls, 1), MAX_BATCH_URLS)
    batch = entries[:cap]
    results: list[dict[str, Any]] = []

    for i, entry in enumerate(batch):
        if i > 0:
            await asyncio.sleep(RATE_LIMIT_DELAY_SECONDS)
        raw_url = str(entry.get("url", ""))
        entity_id = entry.get("entity_id")
        evidence_id = entry.get("evidence_id")
        entity_type: str | None = None
        if entity_id is not None:
            with Session(engine) as session:
                ent = session.get(Entity, int(entity_id))
            if ent is not None:
                entity_type = ent.entity_type
                if not raw_url:
                    raw_url = url_for_entity_check(
                        ent.entity_type, ent.display_value, ent.normalized_value
                    )
        if entity_id is None:
            entity_id = _resolve_entity_id(engine, case_id, raw_url)
        use_http_fallback = fallback_http and (
            entity_type in {"domain", "subdomain", "registration"} or entity_type is None
        )
        probe = await probe_url(
            raw_url,
            settings,
            method=method,
            fallback_get=fallback_get,
            fallback_http=use_http_fallback,
        )
        row = _persist_check(
            engine,
            case_id=case_id,
            entity_id=entity_id,
            evidence_id=evidence_id,
            probe=probe,
        )
        results.append(_row_to_dict(row))

    return {"checked": len(results), "results": results}


def _resolve_entity_id(engine: Engine, case_id: int, url: str) -> int | None:
    normalized = normalize_check_url(url)
    if normalized is None:
        return None
    key = normalized.lower()
    host = urlparse(key).netloc or key.replace("https://", "").replace("http://", "").split("/")[0]
    with Session(engine) as session:
        for ent in session.exec(select(Entity).where(Entity.case_id == case_id)).all():
            if ent.entity_type in _WEB_CHECKABLE_TYPES:
                nv = ent.normalized_value.lower()
                dv = ent.display_value.lower()
                if key in (nv, dv) or host in (nv, dv):
                    return int(ent.id or 0)
    return None


def _persist_check(
    engine: Engine,
    *,
    case_id: int,
    entity_id: int | None,
    evidence_id: int | None,
    probe: dict[str, Any],
) -> UrlLiveCheck:
    row = UrlLiveCheck(
        case_id=case_id,
        entity_id=entity_id,
        evidence_id=evidence_id,
        url=str(probe["url"]),
        method=str(probe.get("method", "HEAD")),
        status=str(probe["status"]),
        status_code=probe.get("status_code"),
        final_url=probe.get("final_url"),
        content_type=probe.get("content_type"),
        content_length=probe.get("content_length"),
        checked_at=probe.get("checked_at") or datetime.now(UTC),
        latency_ms=probe.get("latency_ms"),
        error_message=probe.get("error_message"),
    )
    with Session(engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def list_url_checks(
    engine: Engine,
    case_id: int,
    *,
    status_filter: str | None = None,
    entity_id: int | None = None,
    evidence_id: int | None = None,
    query: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[dict[str, Any]]:
    with Session(engine) as session:
        stmt = select(UrlLiveCheck).where(UrlLiveCheck.case_id == case_id)
        if status_filter:
            stmt = stmt.where(UrlLiveCheck.status == status_filter)
        if entity_id is not None:
            stmt = stmt.where(UrlLiveCheck.entity_id == entity_id)
        if evidence_id is not None:
            stmt = stmt.where(UrlLiveCheck.evidence_id == evidence_id)
        stmt = stmt.order_by(col(UrlLiveCheck.checked_at).desc())
        rows = list(session.exec(stmt).all())
    if query:
        q = query.lower()
        rows = [r for r in rows if q in (r.url or "").lower()]
    page = rows[offset : offset + limit]
    return [_row_to_dict(r) for r in page]


def latest_check_for_evidence(
    engine: Engine, case_id: int, *, entity_id: int | None, evidence_id: int | None
) -> dict[str, Any] | None:
    """Most recent live check linked to an evidence row or its entity."""
    with Session(engine) as session:
        stmt = (
            select(UrlLiveCheck)
            .where(UrlLiveCheck.case_id == case_id)
            .order_by(col(UrlLiveCheck.checked_at).desc())
        )
        rows = list(session.exec(stmt).all())
    for row in rows:
        if evidence_id is not None and row.evidence_id == evidence_id:
            return _row_to_dict(row)
    for row in rows:
        if entity_id is not None and row.entity_id == entity_id:
            return _row_to_dict(row)
    return None


def get_url_check(engine: Engine, check_id: int) -> dict[str, Any] | None:
    with Session(engine) as session:
        row = session.get(UrlLiveCheck, check_id)
    if row is None:
        return None
    return _row_to_dict(row)


def latest_checks_by_entity(engine: Engine, case_id: int) -> dict[int, dict[str, Any]]:
    """Most recent check per entity_id for a case."""
    with Session(engine) as session:
        rows = list(
            session.exec(
                select(UrlLiveCheck)
                .where(UrlLiveCheck.case_id == case_id)
                .where(col(UrlLiveCheck.entity_id).isnot(None))
                .order_by(col(UrlLiveCheck.checked_at).desc())
            ).all()
        )
    by_entity: dict[int, dict[str, Any]] = {}
    for row in rows:
        eid = row.entity_id
        if eid is None or eid in by_entity:
            continue
        by_entity[int(eid)] = _row_to_dict(row)
    return by_entity


def latest_checks_by_url(engine: Engine, case_id: int) -> dict[str, dict[str, Any]]:
    """Most recent check per normalized URL string."""
    with Session(engine) as session:
        rows = list(
            session.exec(
                select(UrlLiveCheck)
                .where(UrlLiveCheck.case_id == case_id)
                .order_by(col(UrlLiveCheck.checked_at).desc())
            ).all()
        )
    by_url: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row.url.lower()
        if key not in by_url:
            by_url[key] = _row_to_dict(row)
    return by_url


def live_quality_reason(status: str | None) -> str | None:
    """Human-readable live-check hint; does not override Wayback historical label."""
    if not status or status == "not_checked":
        return None
    mapping = {
        "live_200": "URL histórica — responde 200 actualmente",
        "redirect": "URL histórica — redirección actual",
        "forbidden": "URL histórica — 403 al comprobar",
        "not_found": "URL histórica — no existe actualmente (404)",
        "server_error": "URL histórica — error del servidor al comprobar",
        "timeout": "URL histórica — estado actual desconocido (timeout)",
        "network_error": "URL histórica — error de red al comprobar",
        "invalid_url": "URL inválida para comprobación",
    }
    return mapping.get(status)
