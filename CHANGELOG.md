# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) ·
Versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

### Changed

- Relicensed the repository from GNU GPL to **MIT**.
- Coverage gate raised to **85 %** (current: ~95 %).

[Unreleased]: https://github.com/rauke10/osint/compare/HEAD
