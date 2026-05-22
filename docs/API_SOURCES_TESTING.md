# API sources testing

How to verify OSINT sources are configured and working **without exposing secrets**.

## Prerequisites

1. Copy `.env.example` → `.env` and fill keys ([API_SOURCES_SETUP.md](API_SOURCES_SETUP.md)).
2. Confirm `.env` is gitignored: `git check-ignore -v .env`
3. **Restart the API** after changing `.env` (settings are loaded at startup).

## Two different concepts

| Concept | Field | When set |
|---------|--------|----------|
| **Credential state** | `credential_status` | `/api/sources/status` (with or without probe) |
| **Last probe / scan outcome** | `probe_scan_status` | Only after `?check=true` or a case scan |

Do not mix them:

- `credential_status=valid` + `probe_scan_status=no_results` → key works, provider returned nothing for the probe target.
- `credential_status=configured_not_checked` → key present in `.env`, not probed yet.
- `credential_status=provider_timeout` → slow provider (crt.sh / Wayback), **not** an invalid key.
- `credential_status=invalid_key` → HTTP 401 (or equivalent) on the **credential probe** endpoint.

Legacy field `status` maps `valid` → `ok` for older clients.

## Check configuration (no HTTP probes)

```bash
uv run globeye sources
curl -s http://127.0.0.1:8000/api/sources/status | jq '.[] | {name, credential_status, configured}'
```

- `configured: true` — required credentials present in settings.
- `credential_status: configured_not_checked` — keys present, run probe to validate.
- Keyless sources: `credential_status: keyless`.

## Credential probe (`?check=true`)

Uses dedicated low-impact endpoints where implemented (see [API_SOURCES_SETUP.md](API_SOURCES_SETUP.md)).

```bash
uv run globeye sources --check
uv run python scripts/diagnose_sources.py --probe
curl -s 'http://127.0.0.1:8000/api/sources/status?check=true' | jq
```

### Response fields (safe)

| Field | Example |
|-------|---------|
| `credential_status` | `valid`, `invalid_key`, `forbidden`, … |
| `probe_scan_status` | `used`, `no_results`, `provider_timeout`, … |
| `http_status` | `401` |
| `provider_error_code` | `AuthenticationRequiredError` |
| `provider_error_message_sanitized` | Short text, secrets redacted |
| `checked_endpoint_name` | `virustotal_domain_info` |
| `auth_method` | `x-apikey header` |
| `checked_at` | ISO timestamp |
| `masked_hint` | `****abcd` |

### `credential_status` values

| Value | Meaning |
|-------|---------|
| `configured_not_checked` | Keys in `.env`, probe not run |
| `valid` | Probe HTTP 200 / auth OK |
| `invalid_key` | HTTP 401 on probe |
| `forbidden` | HTTP 403 (plan / permissions) |
| `rate_limited` | HTTP 429 |
| `missing_key` | Variable not set |
| `incompatible_credentials` | e.g. Censys Platform PAT without Legacy ID+Secret |
| `provider_timeout` | crt.sh / Wayback probe timeout |
| `network_error` | Transport failure |
| `keyless` | No API key required |

### `probe_scan_status` values (after probe)

| Value | Meaning |
|-------|---------|
| `used` | Probe returned data |
| `no_results` | Auth OK, empty result for probe target |
| `provider_timeout` | Provider too slow |
| `network_error` | Could not reach provider |
| `not_applicable` | No probe target for source type |
| `skipped` | Probe skipped (e.g. incompatible Censys config) |

## Manual curl checks (replace `$KEY`)

### AbuseIPDB

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  -H "Key: $GLOBEYE_ABUSEIPDB_API_KEY" -H "Accept: application/json" \
  'https://api.abuseipdb.com/api/v2/check?ipAddress=8.8.8.8&maxAgeInDays=90'
```

- `200` → valid key
- `401` → invalid key
- `403` → forbidden (plan / IP not allowed)

### VirusTotal

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  -H "x-apikey: $GLOBEYE_VIRUSTOTAL_API_KEY" -H "Accept: application/json" \
  'https://www.virustotal.com/api/v3/domains/example.com'
```

### Hunter

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  "https://api.hunter.io/v2/domain-search?domain=example.com&limit=1&api_key=$GLOBEYE_HUNTER_API_KEY"
```

- `403` often means no credits or plan restriction (not always “wrong key”).

### Censys (Legacy Search API)

```bash
curl -s -o /dev/null -w '%{http_code}\n' -u "$GLOBEYE_CENSYS_API_ID:$GLOBEYE_CENSYS_API_SECRET" \
  'https://search.censys.io/api/v1/account'
```

Platform PAT (`censys_…` in one field) → use ID + Secret split, or wait for Platform API support (`GLOBEYE_CENSYS_PLATFORM_TOKEN` reserved).

## UI: case → Fuentes

- Table **last scan** per case (used / no_results / skipped / …).
- Panel **API diagnostics**: credential vs probe; button **Probar credenciales ahora** calls `?check=true`.

## Source routing preview (Fase 2B)

```bash
curl -s -H "X-API-Key: $GLOBEYE_API_KEY" -X POST http://127.0.0.1:8000/api/source-routing/preview \
  -H 'Content-Type: application/json' \
  -d '{"target":"8.8.8.8","depth":"standard"}' | jq '{target_type, profile, will_run: [.will_run[].source]}'
```

## API diagnostics script

```bash
uv run python scripts/diagnose_sources.py          # credentials only
uv run python scripts/diagnose_sources.py --probe  # HTTP probe (masked keys, http_status, how_to_fix)
```

## Troubleshooting real statuses

| Symptom | Likely cause | Action |
|---------|----------------|--------|
| `invalid_key` + HTTP 401 | Wrong or revoked key | Regenerate key in provider portal, update `.env`, restart API |
| `forbidden` + HTTP 403 | Key OK, plan/scope | Upgrade plan or use allowed endpoint |
| `incompatible_credentials` (Censys) | Platform PAT vs Legacy ID+Secret | Split PAT or use Legacy API credentials |
| `provider_timeout` (crt.sh / Wayback) | Slow public service | Retry later; scans can continue without blocking |
| `configured_not_checked` | No probe yet | Run `?check=true` or UI button |
| Key in `.env` but `missing_key` | Typo in variable name | Match [API_SOURCES_SETUP.md](API_SOURCES_SETUP.md) exactly |

## Logs and secrets

- Secrets are `SecretStr` in settings; never returned by `/api/sources/status`.
- `provider_error_message_sanitized` may contain provider text with long tokens redacted.
- Never paste full keys in issues; use `****abcd` hints only.

## Verify Git safety

```bash
git check-ignore .env
```
