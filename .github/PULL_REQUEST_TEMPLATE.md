## Summary

<!-- What does this PR change and why? -->

## Passive-compliance checklist (required)

- [ ] No traffic is sent to any target (no scans/probing/direct DNS or HTTP).
- [ ] No brute force or active enumeration was added.
- [ ] New/updated source hosts are added to the allowlist.
- [ ] Fixtures are **sanitized** (no real keys, IPs, emails, names).

## Quality checklist

- [ ] `make lint` passes (ruff, mypy --strict, bandit).
- [ ] `make test` passes; coverage stays ≥ 85 %.
- [ ] `pip-audit` is clean.
- [ ] Docs updated (`docs/sources.md`, `CHANGELOG.md`) if relevant.

## Notes for reviewers

<!-- Anything reviewers should focus on. -->
