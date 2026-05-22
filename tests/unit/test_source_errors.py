"""Source error formatting for orchestrator skips."""

from __future__ import annotations

import httpx

from globeye.services.source_errors import format_source_error, skip_reason_to_status


def test_format_401_as_invalid_key():
    req = httpx.Request("GET", "https://api.example/")
    resp = httpx.Response(401, request=req)
    err = httpx.HTTPStatusError("unauthorized", request=req, response=resp)
    assert "inválida" in format_source_error(err) or "autorizada" in format_source_error(err)
    assert skip_reason_to_status(format_source_error(err)) == "invalid_key"


def test_format_403_permissions():
    req = httpx.Request("GET", "https://api.example/")
    resp = httpx.Response(403, request=req)
    err = httpx.HTTPStatusError("forbidden", request=req, response=resp)
    msg = format_source_error(err)
    assert "permisos" in msg or "cuota" in msg


def test_format_429_as_rate_limited():
    req = httpx.Request("GET", "https://api.example/")
    resp = httpx.Response(429, request=req)
    err = httpx.HTTPStatusError("too many", request=req, response=resp)
    assert "cuota" in format_source_error(err)
    assert skip_reason_to_status(format_source_error(err)) == "rate_limited"


def test_format_timeout():
    assert "Timeout" in format_source_error(httpx.ReadTimeout("slow"))
    assert skip_reason_to_status("Timeout de red") == "timeout"
