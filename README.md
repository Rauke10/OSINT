<h1 align="center">GLOBEYE</h1>

<p align="center">
  <strong>Strictly passive OSINT toolkit</strong> — infrastructure, identity &amp; organizations.<br>
  Never touches the target. Only queries third parties that already indexed the data.
</p>

<p align="center">
  <a href="https://github.com/rauke10/osint/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/rauke10/osint/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Coverage" src="https://img.shields.io/badge/coverage-%E2%89%A585%25-brightgreen">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue">
  <img alt="Python" src="https://img.shields.io/badge/python-3.12%20%7C%203.13-blue">
  <img alt="Type checked: mypy strict" src="https://img.shields.io/badge/mypy-strict-blue">
</p>

> ⚠️ **LEGAL DISCLAIMER — READ BEFORE USE**
>
> GLOBEYE is an **educational / authorized-assessment** tool. Use it **only**
> against assets you own or for which you hold **explicit written
> authorization**. Passive collection still processes personal data and is
> regulated (GDPR, LECrim, Budapest Convention, and each provider's Terms of
> Service). **You are solely responsible for how you use this software.** The
> author accepts **no liability** for misuse. See
> [`docs/legal.md`](docs/legal.md) and [`SECURITY.md`](SECURITY.md).

---

## Why passive?

Active reconnaissance (port scans, subdomain brute force, direct DNS/HTTP
probing) sends traffic **to the target**: it is noisy, often unauthorized, and
can be unlawful without a contract. **GLOBEYE never contacts the target.** It
only queries third parties that have *already* indexed public information
(Certificate Transparency, RDAP/WHOIS, passive DNS, breach indexes, web
archives, …). This is safer legally and operationally, and leaves no trace on
the target's infrastructure. A test in the suite enforces this invariant: no
request is ever made to the target host.

## Quickstart (3 commands)

```bash
git clone https://github.com/rauke10/osint.git globeye && cd globeye
make install                       # installs Python 3.12/3.13 + deps via uv
uv run globeye scan example.com    # (CLI lands in Phase 2)
```

Or run the API + web UI:

```bash
cp .env.example .env && docker compose up   # UI on http://localhost:8000
```

## Supported targets

Domains · IPs · ASN · CIDR ranges · certificate hashes · emails · usernames ·
phone numbers · real names · company names. The target type is **auto-detected**
from the input, and a scan can **pivot** between types (domain → related emails
→ usernames on public profiles).

## Sources

Full matrix in [`docs/sources.md`](docs/sources.md). Summary:

| Category | Sources | API key required? |
|---|---|---|
| Infrastructure | RDAP/WHOIS, crt.sh, Shodan, Censys, SecurityTrails, AlienVault OTX, Wayback | crt.sh / RDAP / Wayback: **no** · rest: yes |
| Identity | HIBP, Hunter, DeHashed, Gravatar | Gravatar: **no** · rest: yes |
| Code | GitHub code search, Pastebin (via Google CSE) | yes |
| Social | passive public-profile presence check | **no** |

Sources without a key are skipped gracefully; keyless sources always run.

## Roadmap

- [x] **Phase 1** — Scaffolding (structure, tooling, CI, Docker, docs)
- [ ] **Phase 2** — Core + crt.sh source + working CLI
- [ ] **Phase 3** — Remaining infrastructure sources
- [ ] **Phase 4** — Identity & code sources
- [ ] **Phase 5** — Social sources
- [ ] **Phase 6** — Enrichment + pivoting
- [ ] **Phase 7** — FastAPI API + interactive HTML report
- [ ] **Phase 8** — Docs polish, threat model, screenshots, `v0.1.0`

## Development

```bash
make install   # bootstrap
make lint      # ruff + mypy(strict) + bandit
make test      # pytest + coverage
make audit     # pip-audit (dependency CVEs)
```

Architecture: [`docs/architecture.md`](docs/architecture.md) ·
Usage: [`docs/usage.md`](docs/usage.md) ·
Contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md)

## License

[MIT](LICENSE) © 2026 rauke10
