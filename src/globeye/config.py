"""Application settings.

Loaded from the environment / ``.env`` via ``pydantic-settings``. Secrets are
read **only** here and are typed as :class:`~pydantic.SecretStr` so they never
appear in logs or reprs. Nothing is hard-coded; nothing is committed.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlparse

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_VALID_PROXY_SCHEMES = frozenset({"socks5", "http", "https"})


class ProxyConfigError(ValueError):
    """``GLOBEYE_PROXY_URL`` is set but not a valid outbound proxy URL."""


def normalize_proxy_url(value: str | None) -> str | None:
    """Return a proxy URL for httpx, or ``None`` when proxy is disabled.

    Empty, whitespace-only and unset values mean *no proxy*.
    """
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    parsed = urlparse(stripped)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _VALID_PROXY_SCHEMES:
        raise ProxyConfigError(
            "GLOBEYE_PROXY_URL must use socks5://, http:// or https:// "
            f"(got {stripped!r}). Leave empty to disable proxy."
        )
    if not parsed.hostname:
        raise ProxyConfigError(
            f"GLOBEYE_PROXY_URL must include a host (got {stripped!r}). "
            "Leave empty to disable proxy."
        )
    return stripped


class Settings(BaseSettings):
    """Runtime configuration for GLOBEYE."""

    model_config = SettingsConfigDict(
        env_prefix="GLOBEYE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App behaviour ---
    user_agent: str = "GlobeyeOSINT/0.1 (+https://github.com/rauke10/osint)"
    http_timeout_seconds: float = 20.0
    http_max_retries: int = 3
    cache_ttl_seconds: int = 86_400
    cache_dir: str = ".cache"
    cache_enabled: bool = True
    proxy_url: str | None = None
    log_level: str = "INFO"
    log_format: str = "console"

    # --- Enrichment (offline MaxMind GeoLite2 databases, optional) ---
    geoip_city_db: str | None = None
    geoip_asn_db: str | None = None

    # --- Persistence ---
    db_url: str = "sqlite:///./data/globeye.db"

    # --- API server ---
    api_key: SecretStr | None = None
    api_debug: bool = False

    # --- Source credentials (all optional) ---
    shodan_api_key: SecretStr | None = None
    censys_api_id: SecretStr | None = None
    censys_api_secret: SecretStr | None = None
    censys_platform_token: SecretStr | None = None
    crtsh_probe_timeout_seconds: float = 40.0
    wayback_probe_timeout_seconds: float = 45.0
    securitytrails_api_key: SecretStr | None = None
    otx_api_key: SecretStr | None = None
    hibp_api_key: SecretStr | None = None
    hunter_api_key: SecretStr | None = None
    dehashed_email: SecretStr | None = None
    dehashed_api_key: SecretStr | None = None
    github_token: SecretStr | None = None
    google_cse_key: SecretStr | None = None
    google_cse_cx: SecretStr | None = None
    abuseipdb_api_key: SecretStr | None = None
    virustotal_api_key: SecretStr | None = None

    @field_validator("proxy_url", mode="before")
    @classmethod
    def _normalize_proxy_url(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return value  # type: ignore[return-value]
        return normalize_proxy_url(value)

    def secret_values(self) -> set[str]:
        """Every non-empty secret value, for log redaction."""
        out: set[str] = set()
        for name, _ in self.__class__.model_fields.items():
            val = getattr(self, name)
            if isinstance(val, SecretStr):
                raw = val.get_secret_value()
                if raw:
                    out.add(raw)
        return out


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
