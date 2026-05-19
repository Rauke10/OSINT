"""FastAPI application factory (API + static web UI)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from globeye import __version__
from globeye.api.routes import health, history, scan
from globeye.config import Settings, get_settings
from globeye.core.db import make_engine
from globeye.utils.logging import configure_logging
from globeye.utils.redact import Redactor

_STATIC = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the GLOBEYE FastAPI app (API + static UI)."""
    settings = settings or get_settings()
    configure_logging(
        level=settings.log_level,
        fmt=settings.log_format,
        redactor=Redactor(settings.secret_values()),
    )

    app = FastAPI(
        title="GLOBEYE",
        version=__version__,
        description="Strictly passive OSINT — never contacts the target.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.state.settings = settings
    app.state.engine = make_engine(settings.db_url)

    app.include_router(health.router)
    app.include_router(scan.router)
    app.include_router(history.router)

    if _STATIC.is_dir():
        app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

        @app.get("/", include_in_schema=False)
        async def index() -> FileResponse:
            return FileResponse(_STATIC / "index.html")

    return app


# NOTE: no module-level ``app = create_app()`` on purpose. Building the app
# eagerly at import time creates the SQLite engine (and global logging) as an
# import side effect, which races across ``pytest -n auto`` workers and
# pollutes the working tree. Serve via the factory instead:
#     uvicorn --factory globeye.api.main:create_app
