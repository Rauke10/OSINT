"""Configure :class:`~globeye.config.Settings` via env vars in tests.

Avoids ``*_api_key=`` literals in test modules (``detect-secrets`` keyword noise).
Values here are synthetic placeholders, never real credentials.
"""

from __future__ import annotations

from typing import Any

from globeye.config import Settings

_ENV_BY_SHORT: dict[str, str] = {
    "app_key": "GLOBEYE_API_KEY",
    "shodan": "GLOBEYE_SHODAN_API_KEY",
    "abuseipdb": "GLOBEYE_ABUSEIPDB_API_KEY",
    "virustotal": "GLOBEYE_VIRUSTOTAL_API_KEY",
    "hunter": "GLOBEYE_HUNTER_API_KEY",
    "censys_id": "GLOBEYE_CENSYS_API_ID",
    "censys_pass": "GLOBEYE_CENSYS_API_SECRET",
    "censys_pat": "GLOBEYE_CENSYS_PLATFORM_TOKEN",
}


def apply_test_env(monkeypatch: Any, **keys: str | None) -> None:
    for short, value in keys.items():
        if value is not None:
            monkeypatch.setenv(_ENV_BY_SHORT[short], value)


def build_settings(monkeypatch: Any, **kwargs: Any) -> Settings:
    """Apply credential env vars plus optional :class:`Settings` field overrides."""
    env_part = {k: v for k, v in kwargs.items() if k in _ENV_BY_SHORT and v is not None}
    settings_part = {k: v for k, v in kwargs.items() if k not in _ENV_BY_SHORT}
    apply_test_env(monkeypatch, **env_part)
    return Settings(_env_file=None, cache_enabled=False, http_max_retries=0, **settings_part)


def probe_settings(monkeypatch: Any, **keys: str | None) -> Settings:
    return build_settings(monkeypatch, **keys)


def settings_with_db(monkeypatch: Any, tmp_path: Any, **kwargs: Any) -> Settings:
    return build_settings(monkeypatch, db_url=f"sqlite:///{tmp_path}/db.sqlite", **kwargs)
