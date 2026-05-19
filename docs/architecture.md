# Architecture

GLOBEYE is a passive OSINT collector. Input → target detection → concurrent
passive sources → dedup/pivot → persistence → reports (JSON / interactive
HTML). Nothing ever touches the target.

## Component diagram

```mermaid
flowchart TD
    subgraph IF["Interfaces"]
        CLI["CLI — Typer + Rich"]
        API["API — FastAPI + Uvicorn"]
        UI["Web UI — Alpine.js + Tailwind v4"]
    end

    subgraph CORE["Core"]
        TD["Target detector\n(regex + Pydantic validation)"]
        ORCH["Orchestrator\n(asyncio.gather + per-source semaphores)"]
        PIV["Pivot engine\n(--pivot)"]
        MOD["Shared models\n(Finding / Evidence / Confidence)"]
    end

    subgraph SRC["Passive sources (PassiveSource ABC)"]
        INFRA["infra: rdap, crtsh, shodan,\ncensys, securitytrails, otx, wayback"]
        IDN["identity: hibp, hunter,\ndehashed, gravatar"]
        CODE["code: github, pastebin (Google CSE)"]
        SOC["social: passive profile presence"]
    end

    subgraph SUP["Cross-cutting"]
        HTTP["httpx async\n(timeout, retry, SOCKS5/Tor)"]
        RL["Rate limiter"]
        CACHE["Disk TTL cache"]
        RED["structlog + secret/PII redaction"]
        ENR["Enrichment\n(GeoLite2 offline, ASN, reputation)"]
    end

    DB[("SQLite / SQLModel\nscan history")]
    REP["Reports\nJSON · standalone HTML\n(cytoscape graph, timeline)"]

    CLI --> ORCH
    API --> ORCH
    UI --> API
    ORCH --> TD
    ORCH --> SRC
    ORCH --> PIV
    PIV --> ORCH
    SRC --> HTTP
    HTTP --> RL
    HTTP --> CACHE
    HTTP --> RED
    SRC --> MOD
    ORCH --> ENR
    ORCH --> DB
    ORCH --> REP
    REP --> UI
```

## Request lifecycle

1. **Detect** — `core/target.py` classifies the input (domain, IP, ASN, CIDR,
   cert hash, email, username, phone, person, org).
2. **Select** — orchestrator picks sources whose `supported_target_types`
   match and whose required API key (if any) is present.
3. **Execute** — `asyncio.gather` with one `asyncio.Semaphore` per source for
   rate limiting; every call goes through cache → rate limiter → httpx.
4. **Normalize & dedup** — sources return `Finding`s; duplicates collapsed.
5. **Pivot** (optional) — new entities (e.g. a discovered email) enqueue
   follow-up passive scans.
6. **Persist & report** — store in SQLite, emit JSON + interactive HTML.

## Hard invariant

A test snapshots every outbound URL and asserts it belongs to the
**third-party allowlist** and never to the target host. This is what makes
GLOBEYE *provably* passive.
