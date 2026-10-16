# Contributing

Thanks for improving the Virtual PnP platform.  This document defines how work
is proposed, reviewed and merged; it is intentionally short because the
conventions are enforced by tooling (`pre-commit`, `ruff`, `pytest`, CI).

## 1. Branching model

| Branch            | Purpose                                        |
| ----------------- | ---------------------------------------------- |
| `main`            | Always releasable, protected, linear history    |
| `feat/<topic>`    | New capability                                  |
| `fix/<topic>`     | Defect repair                                   |
| `hdl/<block>`     | RTL/verification work                           |
| `flow/<tool>`     | Synthesis / P&R / sign-off flow changes         |

Rebase onto `main` (never merge `main` into a feature branch) so that history
stays linear.

## 2. Commit messages (Conventional Commits)

```
<type>(<scope>): <imperative summary>

<body: why, not what>

<footer: Refs/Closes #issue, BREAKING CHANGE: ...>
```

Allowed types: `feat`, `fix`, `perf`, `refactor`, `test`, `docs`, `build`,
`ci`, `chore`, `hdl`, `flow`.

Scopes used in this repository: `core`, `opt`, `plan`, `vision`, `ml`, `sim`,
`api`, `gui`, `rtl`, `tb`, `formal`, `asic`, `fw`, `docs`, `ci`, `release`.

## 3. Definition of Done

A change is complete only when **all** of the following hold:

1. `make lint` (ruff) and `make typecheck` (mypy) are clean.
2. `make test` passes and coverage of touched modules does not decrease.
3. RTL changes run `make hdl-lint`, `make hdl-synth` and the relevant
   `make formal` proofs; new logic carries SVA properties.
4. Public behaviour is documented (docstring + `docs/` + `CHANGELOG.md`).
5. `requirements`/`pyproject`/toolchain pins updated when dependencies change.

## 4. Review checklist

- [ ] Interfaces frozen (types, units, error contract) before implementation.
- [ ] No magic numbers: physical constants live in `pnp/core/config.py` or
      `rtl/common/pnp_pkg.sv`.
- [ ] Every optimisation reports the baseline it improved and by how much.
- [ ] Failure paths are covered by tests, not only the happy path.

## 5. Release process

1. Update `CHANGELOG.md` (Keep a Changelog format, semantic versioning).
2. `make verify-all` in a clean checkout (bootstrap script).
3. Annotated tag: `git tag -a vX.Y.Z -m "..."` and push the tag.
4. Attach the generated reports (`verification/reports/`, `synthesis/`) to the
   GitHub release.
