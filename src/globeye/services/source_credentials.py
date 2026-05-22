"""Map each passive source to its ``Settings`` / ``.env`` credential fields."""

from __future__ import annotations

from globeye.config import Settings

# source name -> list of Settings attribute names (all must be non-empty)
SOURCE_ENV_FIELDS: dict[str, list[str]] = {
    "shodan": ["shodan_api_key"],
    "censys": ["censys_api_id", "censys_api_secret"],
    # censys_platform_token is optional and not sufficient alone for current integration
    "securitytrails": ["securitytrails_api_key"],
    "otx": ["otx_api_key"],
    "hibp": ["hibp_api_key"],
    "hunter": ["hunter_api_key"],
    "dehashed": ["dehashed_email", "dehashed_api_key"],
    "github": ["github_token"],
    "pastebin": ["google_cse_key", "google_cse_cx"],
    "abuseipdb": ["abuseipdb_api_key"],
    "virustotal": ["virustotal_api_key"],
}

# Human-readable .env variable names (GLOBEYE_ prefix) for docs and status API
SOURCE_ENV_VARS: dict[str, list[str]] = {
    name: [f"GLOBEYE_{field.upper()}" for field in fields]
    for name, fields in SOURCE_ENV_FIELDS.items()
}


def is_configured(settings: Settings, source_name: str, *, requires_api_key: bool) -> bool:
    """Whether credentials for a source are present in settings."""
    if not requires_api_key:
        return True
    fields = SOURCE_ENV_FIELDS.get(source_name)
    if not fields:
        return False
    for field in fields:
        val = getattr(settings, field, None)
        if val is None:
            return False
        raw = val.get_secret_value() if hasattr(val, "get_secret_value") else str(val)
        if not str(raw).strip():
            return False
    return True


def env_vars_for(source_name: str) -> list[str]:
    return SOURCE_ENV_VARS.get(source_name, [])
