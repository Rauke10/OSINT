"""FastAPI application factory (API + static web UI)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from globeye import __version__
from globeye.api.routes import (
    cases,
    data,
    entities,
    evidence,
    health,
    history,
    inventory,
    jobs,
    quality,
    review,
    routing,
    scan,
    url_checks,
)
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
    app.include_router(cases.router)
    app.include_router(jobs.router)
    app.include_router(entities.router)
    app.include_router(evidence.router)
    app.include_router(routing.router)
    app.include_router(quality.router)
    app.include_router(data.router)
    app.include_router(inventory.router)
    app.include_router(review.router)
    app.include_router(url_checks.router)

    # The web UI is the built React SPA (see ``frontend/``). Its assets are a
    # build artefact emitted into ``static/`` by ``npm run build``.
    _STATIC.mkdir(parents=True, exist_ok=True)
    assets = _STATIC / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    def _spa_index() -> Response:
        page = _STATIC / "index.html"
        if page.is_file():
            return FileResponse(page)
        return HTMLResponse(
            "<h1>GLOBEYE</h1><p>The web UI is not built yet. Run "
            "<code>make install</code> (or <code>npm --prefix frontend run "
            "build</code>), then reload.</p>",
            status_code=503,
        )

    @app.get("/", include_in_schema=False)
    async def index() -> Response:
        return _spa_index()

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str, request: Request) -> Response:
        if full_path.startswith("api/") or full_path == "api":
            return HTMLResponse("Not Found", status_code=404)
        if request.url.path.startswith("/assets/"):
            return HTMLResponse("Not Found", status_code=404)
        return _spa_index()

    return app


# NOTE: no module-level ``app = create_app()`` on purpose. Building the app
# eagerly at import time creates the SQLite engine (and global logging) as an
# import side effect, which races across ``pytest -n auto`` workers and
# pollutes the working tree. Serve via the factory instead:
#     uvicorn --factory globeye.api.main:create_app
