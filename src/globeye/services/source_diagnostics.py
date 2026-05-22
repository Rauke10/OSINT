"""Clear per-source diagnostics for analysts (Fase 2C.3)."""

from __future__ import annotations

from typing import Any

from globeye.config import Settings
from globeye.services.source_credentials import env_vars_for, is_configured
from globeye.sources.catalog import label_for

# Display category separate from probe status
UI_CATEGORIES = (
    "executed_ok",
    "executed_empty",
    "not_applicable",
    "missing_key",
    "invalid_key",
    "no_permission",
    "rate_limited",
    "network_error",
    "provider_error",
    "config_error",
    "skipped_by_depth",
    "disabled",
    "unknown",
)

_FIX_HINTS: dict[str, str] = {
    "hibp": "HIBP solo aplica a emails y requiere API key (GLOBEYE_HIBP_API_KEY).",
    "hunter": "Hunter aplica a dominios/emails; verifica GLOBEYE_HUNTER_API_KEY activa.",
    "censys": (
        "Censys requiere API ID + API Secret de Search API v2; "
        "un PAT de Platform v3 puede no servir."
    ),
    "virustotal": (
        "VirusTotal requiere cabecera x-apikey y key activa (GLOBEYE_VIRUSTOTAL_API_KEY)."
    ),
    "abuseipdb": "AbuseIPDB requiere key activa con permisos para el endpoint check.",
    "shodan": "Shodan requiere GLOBEYE_SHODAN_API_KEY con cuota disponible.",
    "securitytrails": "SecurityTrails requiere GLOBEYE_SECURITYTRAILS_API_KEY.",
    "otx": "AlienVault OTX usa GLOBEYE_OTX_API_KEY (opcional pero recomendada).",
    "dehashed": "DeHashed requiere GLOBEYE_DEHASHED_EMAIL y GLOBEYE_DEHASHED_API_KEY.",
    "github": "GitHub requiere GLOBEYE_GITHUB_TOKEN con permisos de búsqueda de código.",
    "pastebin": "Google CSE requiere GLOBEYE_GOOGLE_CSE_KEY y GLOBEYE_GOOGLE_CSE_CX.",
    "rdap": (
        "RDAP usa bootstrap en rdap.org y puede redirigir a servidores de registro "
        "(p. ej. rdap.verisign.com). Deben estar en allowlist."
    ),
}

_STATUS_TO_CATEGORY: dict[str, str] = {
    "ok": "executed_ok",
    "valid": "executed_ok",
    "configured_not_checked": "missing_key",
    "keyless": "executed_ok",
    "missing_key": "missing_key",
    "invalid_key": "invalid_key",
    "forbidden": "no_permission",
    "incompatible_credentials": "config_error",
    "rate_limited": "rate_limited",
    "provider_timeout": "network_error",
    "network_error": "network_error",
    "config_error": "config_error",
    "blocked_by_passive_guard": "config_error",
    "not_applicable": "not_applicable",
    "unknown": "unknown",
}


def _mask_hint(settings: Settings, source_name: str) -> str | None:
    """Return a masked credential hint like ****abcd if configured."""
    from globeye.services.source_credentials import SOURCE_ENV_FIELDS

    fields = SOURCE_ENV_FIELDS.get(source_name)
    if not fields:
        return None
    for field in fields:
        val = getattr(settings, field, None)
        if val is None:
            continue
        raw = val.get_secret_value() if hasattr(val, "get_secret_value") else str(val)
        raw = str(raw).strip()
        if len(raw) >= 4:
            return f"****{raw[-4:]}"
    return None


def enrich_status_row(row: dict[str, Any], settings: Settings) -> dict[str, Any]:
    """Add UI fields: category, fix_hint, env_vars, masked_hint."""
    name = str(row.get("name", ""))
    cred = str(row.get("credential_status") or row.get("status", "unknown"))
    probe_scan = row.get("probe_scan_status")
    category = _STATUS_TO_CATEGORY.get(cred, "unknown")
    message = str(row.get("message") or "")
    if cred in {"ok", "valid", "keyless"} and probe_scan == "no_results":
        category = "executed_empty"
    if (
        cred in {"ok", "valid"}
        and int(row.get("findings_count") or 0) == 0
        and probe_scan == "used"
    ):
        category = "executed_ok"
    if "sin permisos" in message.lower() or cred == "forbidden":
        category = "no_permission"
    if cred == "invalid_key":
        category = "invalid_key"
    if cred == "incompatible_credentials":
        category = "config_error"
    if cred == "blocked_by_passive_guard":
        category = "config_error"
    if cred == "provider_timeout" or probe_scan == "provider_timeout":
        category = "network_error"
    hint = _FIX_HINTS.get(name, "")
    if row.get("how_to_fix"):
        hint = str(row["how_to_fix"])
    elif row.get("provider_error_message_sanitized") and cred in {
        "invalid_key",
        "forbidden",
        "incompatible_credentials",
        "blocked_by_passive_guard",
    }:
        hint = str(row["provider_error_message_sanitized"])
    if category == "missing_key" and cred == "configured_not_checked":
        category = "executed_ok"
        hint = hint or "Credencial configurada; pulsa «Probar credenciales» para validar."
    if category == "missing_key" and not hint:
        hint = f"Configura las variables: {', '.join(env_vars_for(name)) or 'ver documentación'}."
    out = dict(row)
    out["credential_status"] = cred
    out["probe_scan_status"] = probe_scan
    out["ui_category"] = category
    out["fix_hint"] = hint or None
    out["how_to_fix"] = hint or None
    out["env_vars"] = env_vars_for(name)
    out["masked_hint"] = _mask_hint(settings, name)
    out["configured"] = is_configured(
        settings, name, requires_api_key=bool(row.get("requires_api_key"))
    )
    label, desc = label_for(name)
    out["label"] = label
    out["description"] = desc
    return out


def enrich_routing_entry(entry: dict[str, Any], *, bucket: str) -> dict[str, Any]:
    """Tag routing preview rows with bucket (not_applicable, missing_key, skipped_by_depth, …)."""
    out = dict(entry)
    out["routing_bucket"] = bucket
    if bucket == "not_applicable":
        out["ui_category"] = "not_applicable"
    elif bucket == "skipped_missing_key":
        out["ui_category"] = "missing_key"
    elif bucket == "skipped_by_depth":
        out["ui_category"] = "skipped_by_depth"
    elif bucket == "disabled":
        out["ui_category"] = "disabled"
    elif bucket == "will_run":
        out["ui_category"] = "executed_ok"
    else:
        out["ui_category"] = bucket
    name = str(entry.get("source", ""))
    out["fix_hint"] = _FIX_HINTS.get(name)
    return out
