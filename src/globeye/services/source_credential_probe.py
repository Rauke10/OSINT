"""Dedicated credential probes with HTTP status and sanitized provider errors."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from globeye.config import Settings
from globeye.sources.infra.rdap import RdapSource
from globeye.utils.http import DisallowedHostError, build_client

CredentialStatus = Literal[
    "configured_not_checked",
    "valid",
    "invalid_key",
    "forbidden",
    "rate_limited",
    "missing_key",
    "incompatible_credentials",
    "keyless",
    "not_applicable",
    "provider_timeout",
    "network_error",
    "blocked_by_passive_guard",
    "unknown",
]

ProbeScanStatus = Literal[
    "used",
    "no_results",
    "not_applicable",
    "provider_timeout",
    "network_error",
    "skipped",
]

_SECRET_PATTERNS = (
    re.compile(r"(api[_-]?key|token|secret|password)\s*[=:]\s*\S+", re.I),
    re.compile(r"\b[A-Za-z0-9]{32,}\b"),
)


@dataclass
class CredentialProbeResult:
    credential_status: CredentialStatus
    message: str
    probe_scan_status: ProbeScanStatus | None = None
    http_status: int | None = None
    provider_error_code: str | None = None
    provider_error_message_sanitized: str | None = None
    checked_endpoint_name: str | None = None
    auth_method: str | None = None
    findings_count: int = 0

    def legacy_status(self) -> str:
        """Backward-compatible ``status`` for clients expecting ``ok``."""
        if self.credential_status == "valid":
            return "ok"
        if self.credential_status == "keyless" and self.probe_scan_status in {
            "used",
            "no_results",
            None,
        }:
            return "ok"
        return self.credential_status

    def as_dict(self) -> dict[str, Any]:
        return {
            "credential_status": self.credential_status,
            "probe_scan_status": self.probe_scan_status,
            "status": self.legacy_status(),
            "message": self.message,
            "http_status": self.http_status,
            "provider_error_code": self.provider_error_code,
            "provider_error_message_sanitized": self.provider_error_message_sanitized,
            "checked_endpoint_name": self.checked_endpoint_name,
            "auth_method": self.auth_method,
            "findings_count": self.findings_count,
        }


def sanitize_provider_message(text: str | None, *, max_len: int = 240) -> str | None:
    if not text:
        return None
    out = str(text).strip()
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[redacted]", out)
    if len(out) > max_len:
        out = out[: max_len - 3] + "..."
    return out


def _parse_error_body(resp: httpx.Response) -> tuple[str | None, str | None]:
    code: str | None = None
    message: str | None = None
    try:
        data = resp.json()
    except Exception:
        return None, sanitize_provider_message(resp.text[:500])
    if not isinstance(data, dict):
        return None, sanitize_provider_message(str(data)[:500])
    for key in ("error", "errorCode", "code", "message", "errors"):
        if key in data and data[key] is not None:
            val = data[key]
            if key == "errors" and isinstance(val, list) and val:
                val = val[0]
            if isinstance(val, dict):
                code = str(val.get("code") or val.get("id") or code or "")
                message = str(val.get("message") or val.get("error") or message or "")
            else:
                if code is None and key in ("error", "errorCode", "code"):
                    code = str(val)
                else:
                    message = str(val)
    return code or None, sanitize_provider_message(message or json.dumps(data)[:500])


def _credential_from_http(status: int) -> CredentialStatus:
    if status == 200:
        return "valid"
    if status == 401:
        return "invalid_key"
    if status == 403:
        return "forbidden"
    if status == 429:
        return "rate_limited"
    if status >= 500:
        return "unknown"
    return "unknown"


def _host_from_guard_error(exc: DisallowedHostError) -> str:
    text = str(exc)
    marker = "host "
    if marker in text:
        part = text.split(marker, 1)[1]
        return part.strip().strip("'\"").rstrip(")")
    return "unknown"


def guard_blocked_probe_result(
    exc: DisallowedHostError,
    *,
    endpoint_name: str,
    auth_method: str = "none",
) -> CredentialProbeResult:
    host = _host_from_guard_error(exc)
    if endpoint_name.startswith("rdap"):
        detail = (
            f"Passive Guard blocked {host}. RDAP bootstrap may redirect to registry "
            "servers; ensure official RDAP hosts are allowlisted."
        )
    else:
        detail = f"Passive Guard blocked outbound host {host} (not on source allowlist)."
    return CredentialProbeResult(
        credential_status="blocked_by_passive_guard",
        probe_scan_status="skipped",
        message="Blocked by Passive Guard",
        provider_error_code="passive_guard",
        provider_error_message_sanitized=sanitize_provider_message(detail),
        checked_endpoint_name=endpoint_name,
        auth_method=auth_method,
    )


def _scan_from_http(status: int, *, has_data: bool) -> ProbeScanStatus:
    if status != 200:
        if status in {408, 504}:
            return "provider_timeout"
        return "network_error"
    return "used" if has_data else "no_results"


def censys_credential_issue(settings: Settings) -> str | None:
    """Return a human message when Censys env looks like Platform PAT, not Legacy ID+Secret."""
    if settings.censys_platform_token and settings.censys_platform_token.get_secret_value().strip():
        return (
            "GLOBEYE_CENSYS_PLATFORM_TOKEN is set but this integration expects "
            "Legacy Search API ID + Secret (GLOBEYE_CENSYS_API_ID / GLOBEYE_CENSYS_API_SECRET). "
            "Platform PAT support is not enabled yet."
        )

    def _raw(field: str) -> str:
        val = getattr(settings, field, None)
        if val is None:
            return ""
        if hasattr(val, "get_secret_value"):
            return str(val.get_secret_value()).strip()
        return str(val).strip()

    cid, secret = _raw("censys_api_id"), _raw("censys_api_secret")
    if cid.startswith("censys_") or secret.startswith("censys_"):
        return (
            "Credenciales Censys rechazadas: parece un Platform PAT (censys_…). "
            "Esta integración espera Legacy Search API ID + Secret en dos variables."
        )
    if cid and not secret and len(cid) > 24:
        return (
            "Solo GLOBEYE_CENSYS_API_ID está definido con un valor largo; "
            "divide el PAT Legacy en ID y Secret, o usa Platform token en su variable dedicada."
        )
    return None


async def _probe_request(
    settings: Settings,
    *,
    allowed_hosts: set[str],
    method: str,
    url: str,
    endpoint_name: str,
    auth_method: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    probe_timeout: float | None = None,
    retries: int = 0,
    hunter: bool = False,
    count_findings: bool = False,
) -> CredentialProbeResult:
    timeout_sec = probe_timeout if probe_timeout is not None else settings.http_timeout_seconds
    client = build_client(settings, allowed_hosts)
    last_timeout = False
    try:
        for attempt in range(retries + 1):
            try:
                resp = await client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    timeout=timeout_sec,
                )
                code, msg = _parse_error_body(resp)
                cred = _credential_from_http(resp.status_code)
                has_data = False
                if resp.status_code == 200 and count_findings:
                    try:
                        body = resp.json()
                        if isinstance(body, list):
                            has_data = len(body) > 0
                        elif isinstance(body, dict):
                            has_data = bool(body.get("data") or body.get("result") or body)
                        else:
                            has_data = bool(body)
                    except Exception:
                        has_data = bool(resp.text.strip())
                scan = _scan_from_http(resp.status_code, has_data=has_data)
                if cred == "valid":
                    message = f"Probe OK (HTTP {resp.status_code})"
                elif cred == "invalid_key":
                    message = "API key invalid or unauthorized"
                elif cred == "forbidden" and hunter:
                    message = "API key rejected or plan without credits for this endpoint"
                elif cred == "forbidden":
                    message = "API key valid but forbidden for this endpoint or plan"
                elif cred == "rate_limited":
                    message = "Rate limit reached"
                else:
                    message = f"HTTP {resp.status_code} from provider"
                return CredentialProbeResult(
                    credential_status=cred,
                    probe_scan_status=scan,
                    message=message,
                    http_status=resp.status_code,
                    provider_error_code=code,
                    provider_error_message_sanitized=msg,
                    checked_endpoint_name=endpoint_name,
                    auth_method=auth_method,
                )
            except httpx.TimeoutException:
                last_timeout = True
                if attempt < retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                break
            except DisallowedHostError as exc:
                return guard_blocked_probe_result(
                    exc, endpoint_name=endpoint_name, auth_method=auth_method
                )
            except httpx.TransportError as exc:
                return CredentialProbeResult(
                    credential_status="network_error",
                    probe_scan_status="network_error",
                    message="Network error reaching provider",
                    provider_error_message_sanitized=sanitize_provider_message(str(exc)),
                    checked_endpoint_name=endpoint_name,
                    auth_method=auth_method,
                )
    finally:
        await client.aclose()

    if last_timeout:
        return CredentialProbeResult(
            credential_status="provider_timeout",
            probe_scan_status="provider_timeout",
            message="Provider timeout (probe)",
            provider_error_code="provider_timeout",
            provider_error_message_sanitized=(
                "The provider did not respond within the probe timeout."
            ),
            checked_endpoint_name=endpoint_name,
            auth_method=auth_method,
        )
    return CredentialProbeResult(
        credential_status="unknown",
        probe_scan_status="network_error",
        message="Probe failed",
        checked_endpoint_name=endpoint_name,
        auth_method=auth_method,
    )


async def probe_abuseipdb(settings: Settings) -> CredentialProbeResult:
    key = settings.abuseipdb_api_key
    if not key:
        return CredentialProbeResult("missing_key", "Configure credentials in .env")
    api_key = key.get_secret_value()
    return await _probe_request(
        settings,
        allowed_hosts={"api.abuseipdb.com"},
        method="GET",
        url="https://api.abuseipdb.com/api/v2/check",
        endpoint_name="abuseipdb_ip_check",
        auth_method="Key header",
        headers={"Key": api_key, "Accept": "application/json"},
        params={"ipAddress": "8.8.8.8", "maxAgeInDays": 90},
        count_findings=True,
    )


async def probe_virustotal(settings: Settings) -> CredentialProbeResult:
    key = settings.virustotal_api_key
    if not key:
        return CredentialProbeResult("missing_key", "Configure credentials in .env")
    api_key = key.get_secret_value()
    return await _probe_request(
        settings,
        allowed_hosts={"www.virustotal.com"},
        method="GET",
        url="https://www.virustotal.com/api/v3/domains/example.com",
        endpoint_name="virustotal_domain_info",
        auth_method="x-apikey header",
        headers={"x-apikey": api_key, "Accept": "application/json"},
        count_findings=True,
    )


async def probe_hunter(settings: Settings) -> CredentialProbeResult:
    key = settings.hunter_api_key
    if not key:
        return CredentialProbeResult("missing_key", "Configure credentials in .env")
    api_key = key.get_secret_value()
    return await _probe_request(
        settings,
        allowed_hosts={"api.hunter.io"},
        method="GET",
        url="https://api.hunter.io/v2/domain-search",
        endpoint_name="hunter_domain_search",
        auth_method="api_key query param",
        params={"domain": "example.com", "limit": 1, "api_key": api_key},
        hunter=True,
        count_findings=True,
    )


async def probe_censys(settings: Settings) -> CredentialProbeResult:
    issue = censys_credential_issue(settings)
    if issue:
        return CredentialProbeResult(
            credential_status="incompatible_credentials",
            probe_scan_status="skipped",
            message=issue,
            provider_error_code="incompatible_credentials",
            provider_error_message_sanitized=issue,
            checked_endpoint_name="censys_legacy_account",
            auth_method="HTTP Basic (API ID + Secret)",
        )
    cid = settings.censys_api_id
    secret = settings.censys_api_secret
    if not cid or not secret:
        return CredentialProbeResult("missing_key", "Configure Censys API ID and Secret in .env")
    import base64

    token = base64.b64encode(
        f"{cid.get_secret_value()}:{secret.get_secret_value()}".encode()
    ).decode()
    return await _probe_request(
        settings,
        allowed_hosts={"search.censys.io"},
        method="GET",
        url="https://search.censys.io/api/v1/account",
        endpoint_name="censys_legacy_account",
        auth_method="HTTP Basic (API ID + Secret)",
        headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
        count_findings=True,
    )


async def probe_crtsh(settings: Settings) -> CredentialProbeResult:
    result = await _probe_request(
        settings,
        allowed_hosts={"crt.sh"},
        method="GET",
        url="https://crt.sh/",
        endpoint_name="crtsh_ct_lookup",
        auth_method="none",
        params={"q": "%.example.com", "output": "json"},
        probe_timeout=settings.crtsh_probe_timeout_seconds,
        retries=2,
        count_findings=True,
    )
    if result.credential_status == "provider_timeout":
        result.message = "crt.sh probe timeout (provider slow or overloaded)"
        result.provider_error_code = "provider_timeout"
    return result


async def probe_wayback(settings: Settings) -> CredentialProbeResult:
    result = await _probe_request(
        settings,
        allowed_hosts={"web.archive.org"},
        method="GET",
        url="https://web.archive.org/cdx/search/cdx",
        endpoint_name="wayback_cdx_search",
        auth_method="none",
        params={
            "url": "example.com/*",
            "output": "json",
            "fl": "original",
            "collapse": "urlkey",
            "limit": "5",
        },
        probe_timeout=settings.wayback_probe_timeout_seconds,
        retries=2,
        count_findings=True,
    )
    if result.credential_status == "provider_timeout":
        result.message = "Wayback CDX probe timeout (archive.org slow or overloaded)"
        result.provider_error_code = "provider_timeout"
    return result


async def probe_shodan(settings: Settings) -> CredentialProbeResult:
    key = settings.shodan_api_key
    if not key:
        return CredentialProbeResult("missing_key", "Configure credentials in .env")
    api_key = key.get_secret_value()
    return await _probe_request(
        settings,
        allowed_hosts={"api.shodan.io"},
        method="GET",
        url="https://api.shodan.io/dns/domain/example.com",
        endpoint_name="shodan_dns_domain",
        auth_method="key query param",
        params={"key": api_key},
        count_findings=True,
    )


async def probe_rdap(settings: Settings) -> CredentialProbeResult:
    """Probe via rdap.org; allowlist matches :class:`RdapSource` (bootstrap redirects)."""
    return await _probe_request(
        settings,
        allowed_hosts=set(RdapSource.allowed_hosts),
        method="GET",
        url="https://rdap.org/domain/example.com",
        endpoint_name="rdap_domain",
        auth_method="none",
        count_findings=True,
    )


DEDICATED_CREDENTIAL_PROBES: dict[str, Any] = {
    "abuseipdb": probe_abuseipdb,
    "virustotal": probe_virustotal,
    "hunter": probe_hunter,
    "censys": probe_censys,
    "crtsh": probe_crtsh,
    "wayback": probe_wayback,
    "shodan": probe_shodan,
    "rdap": probe_rdap,
}
