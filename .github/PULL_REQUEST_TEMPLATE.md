## Summary

<!-- What changed and why. One paragraph. -->

## Type of change

- [ ] feat  - [ ] fix  - [ ] perf  - [ ] refactor
- [ ] test  - [ ] docs - [ ] ci    - [ ] hdl / flow

## Requirements traceability

| Requirement (docs/SRS.md) | Evidence |
| ------------------------- | -------- |
| SR-xx.x                   | `tests/...`, `verification/reports/...` |

## Verification evidence

<!-- Paste the commands you ran and their result, e.g. `make verify-all` output summary. -->

```
$ make test
...
```

## Risk & rollback

<!-- Impact on safety, interfaces, or released behaviour; how to revert. -->

## Checklist

- [ ] `make lint typecheck test` clean
- [ ] HDL touched -> `make hdl-lint hdl-synth formal` clean
- [ ] `CHANGELOG.md` updated
- [ ] No secrets, generated binaries or oversized artefacts committed
