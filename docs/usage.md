# Usage

> CLI and API land in Phases 2 and 7. This documents the intended interface;
> commands are marked 🚧 until their phase ships.

## Configuration

Copy `.env.example` to `.env` and fill in only the keys you have. Keyless
sources always run; keyed sources are skipped if the key is absent.

```bash
cp .env.example .env
```

Route everything through Tor:

```bash
GLOBEYE_PROXY_URL="socks5://127.0.0.1:9050"
```

## CLI 🚧 (Phase 2+)

```bash
# Scan a domain (type auto-detected)
uv run globeye scan example.com

# Force output + enable pivoting
uv run globeye scan example.com --json out.json --html report.html --pivot

# Other target types
uv run globeye scan 192.0.2.10
uv run globeye scan AS64500
uv run globeye scan jane@example.com
uv run globeye scan "Example Corp"

# Source health checks
uv run globeye sources --health
```

Exit codes: `0` success · `1` runtime error · `2` invalid input.

## API 🚧 (Phase 7)

```bash
make run                       # http://127.0.0.1:8000  (UI at /)
```

```bash
curl -s http://127.0.0.1:8000/api/health
curl -s -X POST http://127.0.0.1:8000/api/scan \
  -H "X-API-Key: $GLOBEYE_API_KEY" \
  -H "content-type: application/json" \
  -d '{"target": "example.com", "pivot": true}'
```

## Docker 🚧

```bash
cp .env.example .env
docker compose up        # API + UI on http://localhost:8000
```

## Reports

- **JSON** — machine-readable findings (`source`, UTC `timestamp`,
  `confidence`, `raw_evidence`, `normalized_data`, `graph_node_hint`).
- **HTML** — single standalone file: filterable table, interactive relation
  graph (cytoscape.js), discovery timeline, print-to-PDF stylesheet, dark
  theme by default (WCAG AA).
