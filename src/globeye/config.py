"""Application settings.

Loaded from the environment / ``.env`` via ``pydantic-settings``. Secrets are
read **only** here and are typed as :class:`~pydantic.SecretStr` so they never
appear in logs or reprs. Nothing is hard-coded; nothing is committed.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    scan_timeout_seconds: float = 300.0
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
    securitytrails_api_key: SecretStr | None = None
    otx_api_key: SecretStr | None = None
    hibp_api_key: SecretStr | None = None
    hunter_api_key: SecretStr | None = None
    dehashed_email: SecretStr | None = None
    dehashed_api_key: SecretStr | None = None
    github_token: SecretStr | None = None
    google_cse_key: SecretStr | None = None
    google_cse_cx: SecretStr | None = None

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
