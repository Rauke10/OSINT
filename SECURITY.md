# Security Policy

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Use **GitHub → Security → Report a vulnerability** (Private Vulnerability
Reporting) on this repository. Include reproduction steps, affected version
and impact. Expected first response: **72 hours**. Coordinated disclosure
after a fix is available (or 90 days, whichever comes first).

## Operational security guarantees

GLOBEYE is engineered so that operating it is itself low-risk:

- **Secrets** are read **only** from environment / `.env` via
  `pydantic-settings`. They are never hard-coded and never committed
  (`.gitignore` + `detect-secrets` pre-commit hook).
- **Log redaction**: `structlog` redacts any value matching known API-key /
  PII patterns to `****` before it is written.
- **Outbound proxy**: all HTTP can be routed through a SOCKS5/HTTP proxy
  (e.g. Tor) via `GLOBEYE_PROXY_URL`.
- **Input validation**: every CLI/API input is validated with Pydantic to
  prevent SSRF, command injection and path traversal.
- **Container hardening**: multi-stage, distroless, non-root (UID 10001),
  read-only filesystem except `/tmp` and `/data`, no new privileges.

## Threat model (summary)

| Asset | Threat | Mitigation |
|---|---|---|
| API keys | Leak via logs / repo | env-only, structlog redaction, detect-secrets |
| Operator identity | Deanonymization by sources | optional Tor/SOCKS5 proxy, generic User-Agent |
| Host running GLOBEYE | SSRF / injection via crafted target | strict Pydantic validation, allowlisted source hosts |
| Target organization | Becoming an active scan | **passive-only invariant + enforcing test** |

### Full threat model

**Scope.** GLOBEYE is a local/self-hosted tool that aggregates public data
from third-party indexes. It has no multi-tenant model; the trust boundary is
the host/container it runs on plus the third-party APIs it calls.

**Assets.** (1) Provider API keys; (2) the operator's network identity;
(3) collected results (personal data); (4) the host running GLOBEYE.

**Adversaries & scenarios.**

| # | Threat | Vector | Mitigation |
|---|---|---|---|
| T1 | API-key disclosure | keys in logs, repo, reports | env-only via `pydantic-settings`; `SecretStr`; structlog redaction; `detect-secrets` pre-commit; keys never written to reports |
| T2 | Accidentally going active | a source contacts the target | per-source host **allowlist** enforced by an httpx request hook; unit + e2e tests assert only allowlisted hosts are contacted |
| T3 | SSRF / injection via target input | crafted CLI/API input | strict Pydantic validation + regex target detection; requests are URL-built from validated values, never raw input; allowlist also bounds egress |
| T4 | Path traversal on report output | attacker-controlled path | reports are written to explicit operator-provided paths only; `Path` + parent-dir creation, no user-derived filenames |
| T5 | Operator deanonymization | sources see operator IP | optional SOCKS5/HTTP proxy (Tor) for **all** egress; generic, configurable User-Agent |
| T6 | Quota exhaustion / provider ToS breach | over-calling APIs | per-source `asyncio` rate limiter (published limits) + disk TTL cache |
| T7 | Sensitive data sprawl | breach creds stored | DeHashed source stores **metadata only**; `.gitignore` excludes `*.db`, `reports/`, `data/`, `.env` |
| T8 | Container escape / privilege | compromised dependency | distroless, non-root (UID 10001), read-only FS, `no-new-privileges`, all caps dropped |
| T9 | Supply-chain CVE | vulnerable dependency | `pip-audit` in CI; pinned `uv.lock`; CodeQL SAST; `bandit` |

**Residual risks.** Third-party indexes may themselves be inaccurate or stale;
results require analyst judgement. GLOBEYE does not anonymize the *content* of
queries sent to providers — use the proxy and minimize queries accordingly.

## Passive-only policy (non-negotiable)

GLOBEYE **must never**:

- send traffic to the target (no port scans, no HTTP requests to the target
  domain, no DNS queries to the target's authoritative server, no service
  probing);
- brute-force subdomains, usernames or credentials;
- perform active enumeration of any kind.

Only third parties that already indexed the data may be queried (RDAP/WHOIS,
crt.sh, Shodan/Censys, HIBP, passive DNS, Wayback, GitHub search, …).

### Sources reviewed and **disallowed** for being active / borderline

| Candidate | Reason it is **excluded** |
|---|---|
| Direct DNS resolution / zone transfer of the target | Active query to the target's authoritative server. |
| Subdomain brute force / DNS wordlists | Active enumeration. |
| SMTP `VRFY`/`RCPT` mailbox checks | Direct probing of the target's mail server. |
| "Live" HTTP screenshotters that fetch the target URL | Direct request to the target. |
| Username checkers that **submit** login/registration forms | Indistinguishable from active probing / may create accounts. |

The social source only reads **already-public** profile pages via indexed
third parties and never authenticates or submits forms. Any future source
whose behaviour is ambiguous between passive and active is **prohibited** and
documented here.
