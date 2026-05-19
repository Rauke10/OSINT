"""Runtime context shared with every source during a scan."""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from globeye.config import Settings
from globeye.utils.cache import DiskCache
from globeye.utils.http import RequestRecorder
from globeye.utils.logging import get_logger


@dataclass(slots=True)
class ScanContext:
    """Carries the settings, cache, logger and request recorder for a scan."""

    settings: Settings
    cache: DiskCache
    recorder: RequestRecorder = field(default_factory=RequestRecorder)

    @classmethod
    def create(cls, settings: Settings) -> ScanContext:
        cache = DiskCache(
            settings.cache_dir,
            settings.cache_ttl_seconds,
            enabled=settings.cache_enabled,
        )
        return cls(settings=settings, cache=cache)

    @property
    def log(self) -> structlog.stdlib.BoundLogger:
        return get_logger("globeye")
