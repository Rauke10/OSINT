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

### Changed

- Relicensed the repository from GNU GPL to **MIT**.

[Unreleased]: https://github.com/rauke10/osint/compare/HEAD
