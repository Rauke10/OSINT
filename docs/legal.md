# Legal notice & disclaimer

> This document is **informative, not legal advice**. Laws differ by
> jurisdiction. When in doubt, consult a lawyer **before** running any scan.

## Authorized use only

GLOBEYE may be used **exclusively** against:

1. assets you **own**, or
2. assets for which you hold **explicit, written authorization** (a signed
   engagement letter, bug-bounty scope, or equivalent) covering passive OSINT.

Any other use may be unlawful. **The author accepts no liability for misuse.**
Even though GLOBEYE is passive, the *results* are personal/organizational data
and their processing and storage is regulated.

## Reference framework

### GDPR — Regulation (EU) 2016/679

Aggregating public data about identifiable people is **processing of personal
data** (Art. 4). You need a **lawful basis** under **Art. 6(1)**:

- **6(1)(f)** legitimate interest — requires a documented balancing test and is
  the usual basis for authorized security assessments; or
- **6(1)(c)** legal obligation, or **6(1)(b)** contract, where applicable.

Also relevant: data minimization and storage limitation (**Art. 5**),
transparency, and **Art. 9** if special-category data is incidentally
collected (delete it). The provider Terms of Service may add constraints.

### Spain — Ley de Enjuiciamiento Criminal (LECrim)

Investigative measures touching communications, traffic data or device data
are reserved to judicial authority (notably the technological-investigation
provisions, arts. 588 *bis* a–588 *octies*). GLOBEYE is **not** an interception
tool and must not be used to circumvent those safeguards. Private actors have
no investigative powers; unlawfully obtained evidence is void
(art. 11 LOPJ).

### Budapest Convention on Cybercrime (ETS No. 185)

Illegal access (Art. 2) and illegal interception (Art. 3) are criminalized by
signatory states. Passive collection from third parties that already published
or indexed the data is **not** access to the target's systems — but using any
finding to gain access is squarely within these offenses.

### Provider Terms of Service

Each source has its own ToS and rate limits (RDAP/WHOIS, crt.sh, Shodan,
Censys, SecurityTrails, AlienVault OTX, Wayback/Internet Archive, HIBP,
Hunter, DeHashed, Gravatar, GitHub, Google CSE). GLOBEYE respects published
rate limits and caches responses, but **you** are responsible for complying
with the ToS of every provider for which you supply credentials. Some ToS
forbid bulk export or redistribution of their data.

## Data handling recommendations

- Treat reports as confidential; store them encrypted, delete when no longer
  needed (storage limitation).
- Do not commit reports, databases or `.env` (enforced by `.gitignore`).
- Honor data-subject rights and breach-notification duties if you retain data.

## Summary

Passive ≠ unregulated. Have authorization, a lawful basis, respect provider
ToS, minimize and protect what you collect.
