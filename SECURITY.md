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

A full threat model lands in Phase 8.

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
