"""structlog configuration with automatic secret/PII redaction."""

from __future__ import annotations

import logging

import structlog

from globeye.utils.redact import Redactor, structlog_redactor

_configured = False


def configure_logging(
    *, level: str = "INFO", fmt: str = "console", redactor: Redactor | None = None
) -> None:
    """Configure structlog once. ``fmt`` is ``console`` or ``json``."""
    global _configured
    redactor = redactor or Redactor()

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if fmt == "json"
        else structlog.dev.ConsoleRenderer(colors=False)
    )

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
        ),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog_redactor(redactor),
            renderer,
        ],
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound logger, configuring defaults lazily."""
    if not _configured:
        configure_logging()
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
