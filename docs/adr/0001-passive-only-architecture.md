# 1. Passive-only architecture

- Status: Accepted
- Date: 2026-05-19

## Context

Reconnaissance tooling spans a spectrum. *Active* techniques — port scans,
subdomain brute force, direct DNS or HTTP probing — send traffic **to the
target**. They are noisy, frequently unauthorized, can be unlawful without a
contract, and leave traces on the target's infrastructure. *Passive*
techniques only read data that third parties have already collected and
indexed.

GLOBEYE is built as an educational and portfolio project. It must be safe to
run against any input and must not be usable as an attack tool.

## Decision

GLOBEYE is **strictly passive**. It never sends a single packet to the target.
Every source queries only third-party indexes that already hold the data
(Certificate Transparency, RDAP/WHOIS, passive DNS, breach indexes, web
archives, and similar).

The invariant is enforced in code, not by convention:

- Each `PassiveSource` declares an explicit allowlist of third-party hosts it
  may contact.
- An `httpx` request event hook rejects any outbound request to a host that
  is not on that source's allowlist.
- The test suite snapshots every outbound URL of an end-to-end scan and
  asserts that the target host never appears.

Active or borderline sources are documented as **disallowed** in
`SECURITY.md` and are rejected in review.

## Consequences

- The tool is safe and lawful to run against any input, and provably so.
- Coverage is bounded by what third parties have already indexed; some data
  an active scan would surface is simply unavailable. This trade-off is
  accepted.
- Every new source must ship a host allowlist and a no-target-traffic test
  before it can be merged.
