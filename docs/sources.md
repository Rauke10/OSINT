# Sources

Every source is **passive**: it queries a third party that already indexed the
data. None of them contact the target. Sources requiring a missing API key are
skipped gracefully; keyless sources always run.

> Status: ✅ all sources are implemented (v0.1.0).

## Infrastructure

| Source | Returns | Targets | API key | Rate limit (free) | Status |
|---|---|---|---|---|---|
| `rdap` | Registration data, registrar, nameservers; pivots contact emails | domain, IP, ASN | No | polite (~1 rps) | ✅ |
| `crtsh` | Subdomains / certificates from Certificate Transparency | domain | No | polite (~0.5 rps) | ✅ |
| `shodan` | Open ports/services + DNS already indexed by Shodan | IP, domain | Yes | plan-dependent | ✅ |
| `censys` | Hosts (services) + certificate name search | IP, domain | Yes | 0.4 rps free | ✅ |
| `securitytrails` | Subdomains via passive DNS | domain | Yes | 50/month free | ✅ |
| `otx` | AlienVault OTX passive DNS | domain, IP | Optional | ~5 rps | ✅ |
| `wayback` | Historical URLs from the Internet Archive (CDX) | domain | No | polite | ✅ |

## Identity

| Source | Returns | Targets | API key | Rate limit (free) | Status |
|---|---|---|---|---|---|
| `hibp` | Breach membership for an email | email | Yes | 1 req / 1.6 s | ✅ |
| `hunter` | Email pattern / known emails for a domain; pivots emails | domain | Yes | plan-dependent | ✅ |
| `dehashed` | Breach **metadata only** (no credential values stored) | email, username | Yes | plan-dependent | ✅ |
| `gravatar` | Public profile for an email hash; pivots username | email | No | polite | ✅ |

## Code

| Source | Returns | Targets | API key | Rate limit (free) | Status |
|---|---|---|---|---|---|
| `github` | Public code-search references | domain, email, org | Yes (token) | ~10 req/min | ✅ |
| `pastebin` | Public pastes via the Google CSE index | domain, email | Yes (CSE) | 100/day free | ✅ |

## Social

| Source | Returns | Targets | API key | Rate limit | Status |
|---|---|---|---|---|---|
| `username_enum` | Presence on public profiles (github, gitlab, reddit, dev.to, Hacker News, keybase) — one read-only GET per platform | username | No | polite | ✅ |

## Disallowed (active / borderline)

See [`SECURITY.md`](../SECURITY.md#sources-reviewed-and-disallowed-for-being-active--borderline)
for the table of rejected candidate sources and the reasoning.
