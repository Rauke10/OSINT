# Sources

Every source is **passive**: it queries a third party that already indexed the
data. None of them contact the target. Sources requiring a missing API key are
skipped gracefully.

> Status legend: ✅ implemented · 🚧 planned (phase noted).

## Infrastructure

| Source | Returns | Targets | API key | Rate limit (free) | Status |
|---|---|---|---|---|---|
| `rdap` | Registration data, registrar, nameservers, org contacts | domain, IP, ASN | No | polite (~1 rps) | 🚧 P3 |
| `crtsh` | Certificates / subdomains from Certificate Transparency | domain | No | polite (~1 rps) | 🚧 P2 |
| `shodan` | Open ports/services already indexed by Shodan | IP, domain | Yes | plan-dependent | 🚧 P3 |
| `censys` | Hosts/certs from Censys search | IP, domain, cert hash | Yes | 0.4 rps free | 🚧 P3 |
| `securitytrails` | Passive DNS, historical records, subdomains | domain, IP | Yes | 50/month free | 🚧 P3 |
| `otx` | AlienVault OTX passive DNS, pulses | domain, IP | Optional | ~10 rps | 🚧 P3 |
| `wayback` | Historical URLs from the Internet Archive (CDX) | domain | No | polite | 🚧 P3 |

## Identity

| Source | Returns | Targets | API key | Rate limit (free) | Status |
|---|---|---|---|---|---|
| `hibp` | Breach membership for an email | email | Yes | 1 req / 1.5 s | 🚧 P4 |
| `hunter` | Email patterns / known emails for a domain | domain, email | Yes | plan-dependent | 🚧 P4 |
| `dehashed` | Breach records | email, username | Yes | plan-dependent | 🚧 P4 |
| `gravatar` | Public profile/avatar for an email hash | email | No | polite | 🚧 P4 |

## Code

| Source | Returns | Targets | API key | Rate limit (free) | Status |
|---|---|---|---|---|---|
| `github` | Public code search hits (leaked refs) | domain, email, org | Yes (token) | 10 req/min (search) | 🚧 P4 |
| `pastebin` | Public pastes via Google CSE index | domain, email | Yes (CSE) | 100/day free | 🚧 P4 |

## Social

| Source | Returns | Targets | API key | Rate limit | Status |
|---|---|---|---|---|---|
| `username_enum` | Presence of a username on public profiles (read-only, via indexed third parties) | username | No | polite | 🚧 P5 |

## Disallowed (active / borderline)

See [`SECURITY.md`](../SECURITY.md#sources-reviewed-and-disallowed-for-being-active--borderline)
for the table of rejected candidate sources and the reasoning.
