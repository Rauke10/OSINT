# Contributing to GLOBEYE

Thanks for your interest! By contributing you agree to the
[Code of Conduct](CODE_OF_CONDUCT.md) and the MIT license.

## Golden rule: stay passive

Any contribution that sends traffic **to a target**, brute-forces, or performs
active enumeration **will be rejected**. New sources must only query third
parties that already indexed the data. See [`SECURITY.md`](SECURITY.md).

## Setup

```bash
make install     # uv + Python 3.12/3.13 + deps + pre-commit hooks
```

## Workflow

1. Branch from `develop`.
2. Make your change with **tests** (coverage must stay **≥ 85 %**).
3. `make lint test` must be green locally.
4. Conventional-ish commits (`feat:`, `fix:`, `docs:`, `test:`, `ci:` …).
5. Open a PR using the template; fill the passive-compliance checklist.

## Adding a new source

- Subclass `PassiveSource` in the right `sources/` subpackage.
- Declare `requires_api_key`, `supported_target_types`, `rate_limit`.
- Add the host to the allowlist (the no-target-traffic test enforces it).
- Add unit tests with **sanitized** fixtures in `tests/fixtures/`
  (no real keys, IPs, emails or names).
- Document it in [`docs/sources.md`](docs/sources.md).

## Quality bars (CI-enforced)

- `ruff` (lint + format), `mypy --strict`, `bandit` clean.
- `pip-audit` reports no vulnerabilities.
- Tests pass on Python 3.12 **and** 3.13, coverage ≥ 85 %, zero flaky tests.
- No secrets / real PII in code or git history.
