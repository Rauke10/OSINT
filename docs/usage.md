# Usage

## Configuration

Copy `.env.example` to `.env` and fill in only the keys you have. Keyless
sources always run; keyed sources are skipped if the key is absent.

```bash
cp .env.example .env
```

Route everything through Tor / a SOCKS5 proxy:

```bash
GLOBEYE_PROXY_URL="socks5://127.0.0.1:9050"
```

## CLI

```bash
# Scan a domain (target type is auto-detected)
uv run globeye scan example.com

# Write reports + enable pivoting
uv run globeye scan example.com --json out.json --html report.html --pivot

# Other target types
uv run globeye scan 192.0.2.10
uv run globeye scan AS64500
uv run globeye scan jane@example.com
uv run globeye scan "Example Corp"

# List sources / health
uv run globeye sources
uv run globeye sources --health
uv run globeye version
```

Options: `--json PATH`, `--html PATH`, `--pivot`, `--no-cache`, `--proxy URL`.
Exit codes: `0` success · `1` runtime error · `2` invalid input.

## API

```bash
make run                       # http://127.0.0.1:8000  (UI at /, docs at /api/docs)
```

```bash
curl -s http://127.0.0.1:8000/api/health

curl -s -X POST http://127.0.0.1:8000/api/scan \
  -H "X-API-Key: $GLOBEYE_API_KEY" \
  -H "content-type: application/json" \
  -d '{"target": "example.com", "pivot": true}'

curl -s http://127.0.0.1:8000/api/history -H "X-API-Key: $GLOBEYE_API_KEY"
# Interactive HTML report for a stored scan:
#   GET /api/scan/{id}/report
```

Set `GLOBEYE_API_KEY` in `.env` (the API refuses to authorize requests when
no key is configured unless `GLOBEYE_API_DEBUG=true`).

## Docker

```bash
cp .env.example .env
docker compose up        # API + UI on http://localhost:8000
```

## Reports

- **JSON** — machine-readable findings (`source`, UTC `timestamp`,
  `confidence`, `raw_evidence`, `normalized_data`, `graph_node_hint`) plus a
  summary block.
- **HTML** — a single self-contained file: filterable/sortable table,
  dependency-free interactive relationship graph, discovery timeline,
  print-to-PDF stylesheet, dark theme by default + light, WCAG-AA.
  See [`sample-report.html`](sample-report.html).

## Enrichment (optional, offline)

Point GLOBEYE at local MaxMind GeoLite2 databases for offline GeoIP/ASN
enrichment (no network lookups ever):

```bash
GLOBEYE_GEOIP_CITY_DB="/data/GeoLite2-City.mmdb"
GLOBEYE_GEOIP_ASN_DB="/data/GeoLite2-ASN.mmdb"
```
