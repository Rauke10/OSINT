"""Secret / PII redaction for logs.

A structlog processor walks every event and replaces (a) any configured
secret value and (b) anything matching a known API-key / token / email
pattern with ``****``. Secrets must never reach disk or stdout.
"""

from __future__ import annotations

import re
from collections.abc import MutableMapping
from typing import Any

MASK = "****"


def mask_secret(value: str, *, tail: int = 4) -> str:
    """Return a display-safe hint for a secret (never log the full value)."""
    stripped = value.strip()
    if not stripped:
        return MASK
    if len(stripped) <= tail:
        return MASK
    return f"{MASK}{stripped[-tail:]}"


# Generic high-signal secret shapes (defence in depth on top of exact values).
_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\b(?:api[_-]?key|token|secret|authorization|bearer)\b\s*[=:]\s*\S+"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),  # GitHub PAT
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\b[A-Za-z0-9]{32,64}\b(?=.*(?:key|token|secret))"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}\b"),  # Google API key
    re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),  # email (PII)
)


class Redactor:
    """Redacts a known set of secret strings plus pattern-based secrets."""

    def __init__(self, secrets: set[str] | None = None) -> None:
        self._secrets = {s for s in (secrets or set()) if s}

    def add_secrets(self, secrets: set[str]) -> None:
        self._secrets.update(s for s in secrets if s)

    def scrub(self, value: Any) -> Any:
        """Recursively redact secrets from arbitrary log values."""
        if isinstance(value, str):
            return self._scrub_str(value)
        if isinstance(value, MutableMapping):
            return {k: self.scrub(v) for k, v in value.items()}
        if isinstance(value, list | tuple | set):
            return type(value)(self.scrub(v) for v in value)
        return value

    def _scrub_str(self, text: str) -> str:
        for secret in self._secrets:
            if secret and secret in text:
                text = text.replace(secret, MASK)
        for pattern in _PATTERNS:
            text = pattern.sub(MASK, text)
        return text


def structlog_redactor(redactor: Redactor) -> Any:
    """Build a structlog processor bound to ``redactor``."""

    def _processor(
        _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        return {k: redactor.scrub(v) for k, v in event_dict.items()}

    return _processor
