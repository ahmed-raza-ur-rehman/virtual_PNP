# Security policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 2.x     | yes       |
| < 2.0   | no        |

## Reporting a vulnerability

Do not open a public issue.  Mail the maintainers with:

* affected component (software / firmware / RTL / flow),
* reproduction steps or a failing test,
* impact assessment (safety, availability, integrity).

You will receive an acknowledgement within 72 hours and a remediation plan
within 10 working days.

## Safety-relevant defects

Anything that can cause uncontrolled axis motion, feeder mis-sequencing or a
missed emergency stop is treated as **critical** and blocks the next release.
Such reports should reference the requirement identifier (`SR-*`) from
`docs/SRS.md` that is at risk.
