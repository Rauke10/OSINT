# API sources setup

GLOBEYE reads third-party credentials from `.env` (never commit this file).
Pydantic prefix: **`GLOBEYE_`** + field name in **UPPER_SNAKE_CASE**.

## Variable map (code ↔ `.env`)

| Source | Settings field(s) | `.env` variable(s) |
|--------|-------------------|-------------------|
| Shodan | `shodan_api_key` | `GLOBEYE_SHODAN_API_KEY` |
| Censys | `censys_api_id`, `censys_api_secret` | `GLOBEYE_CENSYS_API_ID`, `GLOBEYE_CENSYS_API_SECRET` |
| Censys (reserved) | `censys_platform_token` | `GLOBEYE_CENSYS_PLATFORM_TOKEN` (not used by scans yet) |
| SecurityTrails | `securitytrails_api_key` | `GLOBEYE_SECURITYTRAILS_API_KEY` |
| AlienVault OTX | `otx_api_key` | `GLOBEYE_OTX_API_KEY` |
| HIBP | `hibp_api_key` | `GLOBEYE_HIBP_API_KEY` |
| Hunter.io | `hunter_api_key` | `GLOBEYE_HUNTER_API_KEY` |
| DeHashed | `dehashed_email`, `dehashed_api_key` | `GLOBEYE_DEHASHED_EMAIL`, `GLOBEYE_DEHASHED_API_KEY` |
| GitHub | `github_token` | `GLOBEYE_GITHUB_TOKEN` |
| Pastebin (Google CSE) | `google_cse_key`, `google_cse_cx` | `GLOBEYE_GOOGLE_CSE_KEY`, `GLOBEYE_GOOGLE_CSE_CX` |
| AbuseIPDB | `abuseipdb_api_key` | `GLOBEYE_ABUSEIPDB_API_KEY` |
| VirusTotal | `virustotal_api_key` | `GLOBEYE_VIRUSTOTAL_API_KEY` |

### Keyless sources (no `.env` entry)

- `crt.sh`, `rdap`, `wayback`, `gravatar`, `username_enum`

### Censys: Legacy Search API vs Platform PAT

**GLOBEYE scans and credential probes use the Legacy Search API** (`search.censys.io`) with HTTP Basic auth:

- Probe: `GET https://search.censys.io/api/v1/account`
- Scans: Search API v2 hosts/certificates

If your token looks like `censys_<ID>_<SECRET>`:

- `GLOBEYE_CENSYS_API_ID` = `<ID>` (e.g. `32AeSQJJ`)
- `GLOBEYE_CENSYS_API_SECRET` = `<SECRET>` (remainder after the second `_`)

Do **not** put the full `censys_…` string in a single variable.
If only a Platform PAT is available, status will be `incompatible_credentials` until Platform API support is added.

Optional (reserved): `GLOBEYE_CENSYS_PLATFORM_TOKEN` — documented for future Platform API; not used by current integration.

### Probe timeouts (keyless)

| Setting | Default | `.env` |
|---------|---------|--------|
| `crtsh_probe_timeout_seconds` | 40s | `GLOBEYE_CRTSH_PROBE_TIMEOUT_SECONDS` |
| `wayback_probe_timeout_seconds` | 45s | `GLOBEYE_WAYBACK_PROBE_TIMEOUT_SECONDS` |

crt.sh and Wayback use longer timeouts and 2 retries on **credential probe only**; failures are `provider_timeout`, not `invalid_key`.

### Outbound proxy

| Field | `.env` |
|-------|--------|
| `proxy_url` | `GLOBEYE_PROXY_URL` |

Leave **empty** to disable proxy. Only `socks5://`, `http://`, `https://` with a host are accepted.

## Quick check

```bash
uv run globeye sources --check
# or without network probes (credentials only):
uv run globeye sources

uv run python scripts/check_sources.py --probe
curl -s 'http://127.0.0.1:8000/api/sources/status?check=true' | jq
```

See [API_SOURCES_TESTING.md](API_SOURCES_TESTING.md) for full test procedures.

## Credential probe endpoints (check=true)

| Source | Endpoint | Auth |
|--------|----------|------|
| AbuseIPDB | `GET /api/v2/check?ipAddress=8.8.8.8&maxAgeInDays=90` | `Key` header |
| VirusTotal | `GET /api/v3/domains/example.com` | `x-apikey` header |
| Hunter | `GET /v2/domain-search?domain=example.com&limit=1` | `api_key` query |
| Censys | `GET /api/v1/account` | HTTP Basic ID:Secret |
| crt.sh | `GET /?q=%.example.com&output=json` | none |
| Wayback | `GET /cdx/search/cdx?url=example.com/*&limit=5` | none |
| Others | Source `fetch()` with probe target | per source |

Restart the API after editing `.env`. Configured ≠ validated until `?check=true`.

## Smart routing (Fase 2B)

Case scans and `POST /api/source-routing/preview` use **target profiles** so only relevant sources run.
Legacy `POST /api/scan` still queries all applicable sources. Details: [PHASE_2B_SOURCE_ROUTING.md](PHASE_2B_SOURCE_ROUTING.md).
