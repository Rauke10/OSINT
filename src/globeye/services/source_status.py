"""Passive source configuration checks and optional light probes."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, Literal, cast

import httpx

from globeye.config import Settings
from globeye.core.context import ScanContext
from globeye.core.models import Target, TargetType
from globeye.core.target import detect
from globeye.services.source_credential_probe import (
    DEDICATED_CREDENTIAL_PROBES,
    CredentialProbeResult,
    censys_credential_issue,
    guard_blocked_probe_result,
    sanitize_provider_message,
)
from globeye.services.source_credentials import env_vars_for, is_configured
from globeye.services.source_errors import format_source_error
from globeye.sources.base import PassiveSource, discover_sources
from globeye.sources.catalog import label_for
from globeye.utils.http import DisallowedHostError

SourceStatusCode = Literal[
    "ok",
    "missing_key",
    "invalid_key",
    "forbidden",
    "rate_limited",
    "network_error",
    "provider_timeout",
    "incompatible_credentials",
    "configured_not_checked",
    "config_error",
    "not_applicable",
    "unknown",
    "keyless",
    "blocked_by_passive_guard",
]

_PROBE_BY_TYPE: dict[TargetType, Target] = {
    TargetType.DOMAIN: detect("example.com"),
    TargetType.IP: detect("8.8.8.8"),
    TargetType.EMAIL: detect("test@example.com"),
    TargetType.USERNAME: detect("example"),
}


def _pick_probe_target(src: PassiveSource) -> Target | None:
    for ttype in src.supported_target_types:
        if ttype in _PROBE_BY_TYPE:
            return _PROBE_BY_TYPE[ttype]
    return None


def _status_from_exception(exc: BaseException) -> tuple[str, int | None, str | None, str | None]:
    """Map fetch() exception to credential status + HTTP metadata."""
    if isinstance(exc, DisallowedHostError):
        blocked = guard_blocked_probe_result(exc, endpoint_name="source_fetch")
        return (
            "blocked_by_passive_guard",
            None,
            blocked.provider_error_code,
            blocked.provider_error_message_sanitized,
        )
    if isinstance(exc, httpx.HTTPStatusError):
        resp = exc.response
        code, msg = None, None
        try:
            data = resp.json()
            if isinstance(data, dict):
                err = data.get("error") or data.get("message")
                if err is not None:
                    code = str(err) if not isinstance(err, dict) else str(err.get("code") or err)
                    msg = sanitize_provider_message(
                        str(err.get("message") if isinstance(err, dict) else err)
                    )
        except Exception:
            msg = sanitize_provider_message(resp.text[:300])
        status_code = resp.status_code
        if status_code == 401:
            return "invalid_key", status_code, code, msg
        if status_code == 403:
            return "forbidden", status_code, code, msg
        if status_code == 429:
            return "rate_limited", status_code, code, msg
        if status_code >= 500:
            return "unknown", status_code, code, msg
        return "unknown", status_code, code, msg
    if isinstance(exc, httpx.TimeoutException):
        return "provider_timeout", None, "provider_timeout", "Provider timeout"
    if isinstance(exc, httpx.TransportError):
        return "network_error", None, None, sanitize_provider_message(str(exc))
    reason = format_source_error(exc)
    lower = reason.lower()
    if "inválida" in lower or "invalid api key" in lower or "no autorizada" in lower:
        return "invalid_key", None, None, sanitize_provider_message(reason)
    if "sin permisos" in lower or "forbidden" in lower:
        return "forbidden", None, None, sanitize_provider_message(reason)
    if "cuota" in lower or "rate limit" in lower:
        return "rate_limited", None, None, sanitize_provider_message(reason)
    if "timeout" in lower:
        return "provider_timeout", None, "provider_timeout", sanitize_provider_message(reason)
    if "network" in lower:
        return "network_error", None, None, sanitize_provider_message(reason)
    return "unknown", None, None, sanitize_provider_message(reason)


def _row_base(cls: type[PassiveSource], settings: Settings) -> dict[str, Any]:
    label, desc = label_for(cls.name)
    configured = is_configured(settings, cls.name, requires_api_key=cls.requires_api_key)
    return {
        "name": cls.name,
        "label": label,
        "description": desc,
        "requires_api_key": cls.requires_api_key,
        "configured": configured,
        "env_vars": env_vars_for(cls.name),
        "targets": sorted(t.value for t in cls.supported_target_types),
    }


def _apply_probe_result(row: dict[str, Any], result: CredentialProbeResult) -> None:
    row.update(result.as_dict())


def _row_probe_failure(row: dict[str, Any], exc: BaseException, *, endpoint: str) -> dict[str, Any]:
    """Turn a probe failure into a per-source status row (never raise)."""
    if isinstance(exc, DisallowedHostError):
        result = guard_blocked_probe_result(exc, endpoint_name=endpoint)
        row.update(result.as_dict())
        return row
    root: BaseException = exc
    while isinstance(root, RuntimeError) and root.__cause__ is not None:
        root = root.__cause__
    if isinstance(root, DisallowedHostError):
        result = guard_blocked_probe_result(root, endpoint_name=endpoint)
        row.update(result.as_dict())
        return row
    cred, http_status, code, msg = _status_from_exception(root)
    row.update(
        {
            "credential_status": cred,
            "status": "ok" if cred == "valid" else cred,
            "probe_scan_status": (
                "provider_timeout"
                if cred == "provider_timeout"
                else "network_error"
                if cred in {"network_error", "unknown"}
                else "skipped"
            ),
            "message": format_source_error(exc),
            "findings_count": 0,
            "http_status": http_status,
            "provider_error_code": code,
            "provider_error_message_sanitized": msg,
            "checked_endpoint_name": endpoint,
        }
    )
    return row


async def _run_dedicated_probe(name: str, settings: Settings) -> CredentialProbeResult:
    probe_fn = cast(
        Callable[[Settings], Awaitable[CredentialProbeResult]],
        DEDICATED_CREDENTIAL_PROBES[name],
    )
    try:
        return await probe_fn(settings)
    except DisallowedHostError as exc:
        return guard_blocked_probe_result(exc, endpoint_name=f"{name}_probe")


async def describe_source_status(
    settings: Settings,
    *,
    probe: bool = False,
) -> list[dict[str, Any]]:
    """Build a status row per registered source (optional credential probe)."""
    probe_settings = settings.model_copy(update={"cache_enabled": False, "http_max_retries": 0})
    ctx = ScanContext.create(probe_settings)

    async def _one(cls: type[PassiveSource]) -> dict[str, Any]:
        row = _row_base(cls, settings)
        src = cls(ctx)
        try:
            try:
                if not cls.requires_api_key:
                    row["credential_status"] = "keyless"
                    row["status"] = "keyless"
                    row["message"] = "No API key required"
                    if not probe:
                        row["probe_scan_status"] = None
                        return row
                    if cls.name in DEDICATED_CREDENTIAL_PROBES:
                        _apply_probe_result(row, await _run_dedicated_probe(cls.name, settings))
                        return row
                    target = _pick_probe_target(src)
                    if target is None or not src.applicable(target):
                        row["credential_status"] = "not_applicable"
                        row["status"] = "not_applicable"
                        row["probe_scan_status"] = "not_applicable"
                        row["message"] = "No probe target for this source"
                        return row
                    row.update(await _probe_via_fetch(src, target))
                    return row

                if cls.name == "censys":
                    issue = censys_credential_issue(settings)
                    if issue:
                        row["credential_status"] = "incompatible_credentials"
                        row["status"] = "incompatible_credentials"
                        row["message"] = issue
                        row["probe_scan_status"] = "skipped" if probe else None
                        row["provider_error_message_sanitized"] = issue
                        row["how_to_fix"] = issue
                        return row

                if not row["configured"]:
                    row["credential_status"] = "missing_key"
                    row["status"] = "missing_key"
                    row["message"] = "Configure credentials in .env"
                    row["probe_scan_status"] = None
                    return row

                if not src.available():
                    row["credential_status"] = "missing_key"
                    row["status"] = "missing_key"
                    row["message"] = "Credentials incomplete in .env"
                    row["probe_scan_status"] = None
                    return row

                if not probe:
                    row["credential_status"] = "configured_not_checked"
                    row["status"] = "configured_not_checked"
                    row["message"] = "Credentials configured (run with check=true to probe)"
                    row["probe_scan_status"] = None
                    return row

                if cls.name in DEDICATED_CREDENTIAL_PROBES:
                    _apply_probe_result(row, await _run_dedicated_probe(cls.name, settings))
                    return row

                target = _pick_probe_target(src)
                if target is None or not src.applicable(target):
                    row["credential_status"] = "configured_not_checked"
                    row["status"] = "configured_not_checked"
                    row["message"] = "Credentials configured (no probe target)"
                    row["probe_scan_status"] = "not_applicable"
                    return row
                row.update(await _probe_via_fetch(src, target))
                return row
            except DisallowedHostError as exc:
                return _row_probe_failure(row, exc, endpoint=f"{cls.name}_probe")
            except httpx.HTTPError as exc:
                return _row_probe_failure(row, exc, endpoint=f"{cls.name}_probe")
            except Exception as exc:
                return _row_probe_failure(row, exc, endpoint=f"{cls.name}_probe")
        finally:
            await src.aclose()

    results = await asyncio.gather(*(_one(cls) for cls in discover_sources()))
    checked_at = datetime.now(UTC).isoformat()
    for row in results:
        row["checked_at"] = checked_at if probe else None
    return sorted(results, key=lambda r: str(r["name"]))


async def _probe_via_fetch(src: PassiveSource, target: Target) -> dict[str, Any]:
    try:
        findings = await src.fetch(target)
        count = len(findings)
        return {
            "credential_status": "valid",
            "status": "ok",
            "probe_scan_status": "used" if count else "no_results",
            "message": f"Probe OK ({count} finding{'s' if count != 1 else ''})",
            "findings_count": count,
            "http_status": 200,
            "checked_endpoint_name": f"{src.name}_fetch",
            "auth_method": "source default",
        }
    except Exception as exc:
        root: BaseException = exc
        while isinstance(root, RuntimeError) and root.__cause__ is not None:
            root = root.__cause__
        cred, http_status, code, msg = _status_from_exception(root)
        return {
            "credential_status": cred,
            "status": "ok" if cred == "valid" else cred,
            "probe_scan_status": (
                "provider_timeout"
                if cred == "provider_timeout"
                else "network_error"
                if cred == "network_error"
                else "skipped"
            ),
            "message": format_source_error(exc),
            "findings_count": 0,
            "http_status": http_status,
            "provider_error_code": code,
            "provider_error_message_sanitized": msg,
            "checked_endpoint_name": f"{src.name}_fetch",
            "auth_method": "source default",
        }
