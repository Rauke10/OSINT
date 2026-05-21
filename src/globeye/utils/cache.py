"""On-disk TTL cache so we never burn third-party API quotas needlessly."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class DiskCache:
    """A tiny JSON file cache keyed by ``namespace`` + request signature."""

    def __init__(self, directory: str | Path, ttl_seconds: int, *, enabled: bool = True) -> None:
        self.dir = Path(directory)
        self.ttl = ttl_seconds
        self.enabled = enabled

    def _path(self, namespace: str, key: str) -> Path:
        digest = hashlib.sha256(f"{namespace}:{key}".encode()).hexdigest()
        return self.dir / namespace / f"{digest}.json"

    def get(self, namespace: str, key: str) -> Any | None:
        """Return the cached value or ``None`` if missing/expired/disabled."""
        if not self.enabled:
            return None
        path = self._path(namespace, key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if time.time() - float(payload.get("_ts", 0)) > self.ttl:
            return None
        return payload.get("data")

    def set(self, namespace: str, key: str, data: Any) -> None:
        """Store ``data`` for ``namespace``/``key`` (no-op when disabled)."""
        if not self.enabled:
            return
        path = self._path(namespace, key)
        # Caching is best-effort: a write failure (e.g. read-only filesystem)
        # must never break a scan.
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps({"_ts": time.time(), "data": data}, default=str),
                encoding="utf-8",
            )
            tmp.replace(path)
        except OSError:
            return
