"""Proxy URL normalization and HTTP client behaviour."""

from __future__ import annotations

import httpx
import pytest

from globeye.config import ProxyConfigError, Settings, normalize_proxy_url
from globeye.utils.http import build_client, request_json


def test_normalize_proxy_empty_string_is_none() -> None:
    assert normalize_proxy_url("") is None
    assert normalize_proxy_url("   ") is None
    assert normalize_proxy_url(None) is None


def test_settings_proxy_url_empty_env_value() -> None:
    s = Settings(_env_file=None, proxy_url="")
    assert s.proxy_url is None


def test_settings_proxy_url_none() -> None:
    s = Settings(_env_file=None, proxy_url=None)
    assert s.proxy_url is None


def test_settings_proxy_url_socks5() -> None:
    url = "socks5://127.0.0.1:9050"
    s = Settings(_env_file=None, proxy_url=url)
    assert s.proxy_url == url


def test_normalize_proxy_invalid_scheme_raises() -> None:
    with pytest.raises(ProxyConfigError, match="socks5://, http:// or https://"):
        normalize_proxy_url("not-a-proxy")


def test_normalize_proxy_missing_host_raises() -> None:
    with pytest.raises(ProxyConfigError, match="must include a host"):
        normalize_proxy_url("http://")


async def test_build_client_empty_proxy_works(settings, respx_mock) -> None:
    settings_empty = Settings(_env_file=None, proxy_url="")
    assert settings_empty.proxy_url is None
    respx_mock.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=[]))
    client = build_client(settings_empty, {"crt.sh"})
    data = await request_json(client, "GET", "https://crt.sh/", settings=settings_empty)
    await client.aclose()
    assert data == []


async def test_build_client_no_proxy_uses_none(settings, respx_mock) -> None:
    assert settings.proxy_url is None
    respx_mock.get("https://crt.sh/").mock(return_value=httpx.Response(200, json={"ok": True}))
    client = build_client(settings, {"crt.sh"})
    data = await request_json(client, "GET", "https://crt.sh/", settings=settings)
    await client.aclose()
    assert data == {"ok": True}
