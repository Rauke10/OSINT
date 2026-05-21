# 2. Source registry and self-registration

- Status: Accepted
- Date: 2026-05-19

## Context

GLOBEYE has many passive sources and is expected to gain more. The
orchestrator needs the set of available sources, but it should not import or
name each one explicitly. A central list that every new source must edit
creates merge friction and couples the core to every source module.

## Decision

Sources **self-register**. Each source subclasses the `PassiveSource`
abstract base class and is marked with a `@register` decorator that adds it to
a process-wide registry keyed by source name.

At start-up, `discover_sources()` walks the `globeye.sources` package with
`pkgutil` — recursively, into `infra/`, `identity/`, `code/`, `social/` and
`intel/` — and imports every module, which triggers the decorators. The
orchestrator then reads the populated registry.

Adding a source is therefore a single self-contained file: no central list,
no edit to the core.

## Consequences

- New sources drop in as one file; the core never changes.
- Discovery is import-driven, so a module with an import-time error fails
  loudly at start-up instead of being silently skipped.
- The registry is global process state; tests that need isolation operate on
  the registry explicitly rather than re-importing modules.
- A separate, human-facing `sources/catalog.py` describes sources for the UI
  and reports. It is descriptive metadata, kept distinct from the runtime
  registry.
