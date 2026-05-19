"""Simple API-key auth for the self-hosted API."""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.engine import Engine

from globeye.config import Settings


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_engine(request: Request) -> Engine:
    engine: Engine = request.app.state.engine
    return engine


async def require_api_key(
    settings: Annotated[Settings, Depends(get_settings)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """Reject requests without a valid ``X-API-Key`` header.

    In debug mode (``GLOBEYE_API_DEBUG=true``) auth is bypassed. If no key is
    configured and not in debug mode, the API is considered misconfigured.
    """
    if settings.api_debug:
        return
    configured = settings.api_key.get_secret_value() if settings.api_key else ""
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key not configured (set GLOBEYE_API_KEY)",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing API key",
        )
