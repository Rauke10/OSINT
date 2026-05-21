# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) ·
Versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **React + TypeScript web UI** (`frontend/`, Vite + Tailwind v4): a
  professional single-page interface — scan form, summary cards,
  "Sources consulted" panel, interactive cytoscape relationship graph,
  filterable/paginated findings table, scan-history browser, JSON /
  HTML-report export, dark/light theme and an **ES/EN bilingual** toggle.
- `GET /api/sources` and the shared `globeye.sources.catalog`.

### Changed

- The web UI is now the built React SPA (replacing the Alpine.js page).
  It is a build artefact emitted into the package by `npm run build`;
  FastAPI serves it. `make install` / the Dockerfile build it; the CI
  gained a frontend typecheck+build job.

### Fixed

- Source failures now report a short, human reason (e.g.
  `HTTP 403 (blocked — the source rejected the request)`) instead of a raw
  multi-line `RuntimeError` dump.
- `4xx` responses other than 429 (e.g. 403) fail fast instead of being
  retried with back-off — a blocked scan now finishes in ~0.2 s, not ~8 s.
- The disk cache is now strictly best-effort: a write failure (e.g.
  read-only filesystem) no longer aborts the source.
- `.env.example` no longer ships relative `GLOBEYE_DB_URL` /
  `GLOBEYE_CACHE_DIR` values that broke the read-only Docker container;
  they default to the writable `/data` paths. Clarified that
  `GLOBEYE_API_KEY` is a secret you generate yourself.

## [0.1.0] — 2026-05-19

First public release: a complete, strictly passive OSINT toolkit.

### Added

- **Phase 8 — Release polish**: full threat model in `SECURITY.md`,
  finalized `docs/` (sources/usage/architecture/legal), an illustrative
  UI mock (`docs/screenshots/ui.svg`), a real generated example report
  (`docs/sample-report.html`), README screenshot/quickstart, and the
  `v0.1.0` release.

- **Phase 1 — Scaffolding**: repository structure, `pyproject.toml` (uv),
  ruff / mypy(strict) / bandit / pip-audit configuration, GitHub Actions CI
  (Python 3.12 & 3.13) + CodeQL, multi-stage distroless Dockerfile,
  `docker-compose.yml`, `Makefile`, pre-commit (incl. detect-secrets),
  `.env.example`, MIT `LICENSE`, `SECURITY.md` (passive-only policy +
  disallowed-sources table), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  initial documentation (`docs/architecture.md`, `sources.md`, `usage.md`,
  `legal.md`) and README.

- **Phase 2 — Core + first source**: shared Pydantic v2 models
  (`Target`, `Finding`, `Evidence`, `Confidence`, `ScanResult`, `RateLimit`,
  `SourceStatus`), automatic target detection/normalization (offline
  `tldextract`), `ScanContext`, async HTTP client with the **passive guard**
  (allowlisted hosts only — provably never the target), disk TTL cache,
  per-source async rate limiter, structlog logging with secret/PII
  redaction, `PassiveSource` ABC + self-registering source registry, the
  **crt.sh** source, the concurrent `Orchestrator` (dedup + pivot), the
  JSON report writer and a working **Typer + Rich CLI**
  (`globeye scan/sources/version`).

- **Phase 3 — Infrastructure sources**: `rdap` (domain/IP/ASN, pivots
  contact emails), `shodan` (host services + DNS), `censys` (host view +
  certificate name search), `securitytrails` (subdomains), `otx`
  (passive DNS, keyless), `wayback` (Internet Archive CDX). Each with a
  tight host allowlist, sanitized fixtures and the no-target-traffic test.

- **Phase 4 — Identity & code sources**: `hibp` (breach membership),
  `hunter` (domain emails, pivots), `dehashed` (breach metadata only —
  credential values are deliberately discarded), `gravatar` (keyless,
  pivots username), `github` (code search), `pastebin` (via Google CSE).

- **Phase 5 — Social source**: `username_enum` — one deterministic,
  read-only GET per platform (github, gitlab, reddit, dev.to, Hacker News,
  keybase). No brute force, no auth, no form submission.

- **Phase 6 — Enrichment & pivoting**: offline GeoLite2 City/ASN enricher
  (no network; no-op without local `.mmdb`), deterministic offline
  reputation tagging (`sensitive`/`notable`/`info`), ASN helpers, and
  `derive_pivots` (domain → emails → usernames) wired into the
  orchestrator.

- **Phase 7 — API & interactive report**: FastAPI app (`/api/health`,
  `/api/scan`, `/api/history`, HTML report endpoint) with simple
  constant-time API-key auth, SQLite/SQLModel scan history, a
  self-contained interactive HTML report (filterable/sortable table,
  dependency-free SVG relationship graph, discovery timeline, print/PDF
  stylesheet, dark/light, WCAG-AA), a cytoscape-compatible graph builder,
  and an Alpine.js + Tailwind static UI. `globeye scan --html` added.
  Integration + end-to-end tests included.

### Changed

- Relicensed the repository from GNU GPL to **MIT**.
- Coverage gate raised to **85 %** (current: ~95 %).

[Unreleased]: https://github.com/rauke10/osint/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/rauke10/osint/releases/tag/v0.1.0
