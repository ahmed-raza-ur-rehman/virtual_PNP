# Requirements traceability matrix

**Document:** VP-TRM-001 · **Version:** 2.1

Each requirement from `docs/SRS.md` is traced to the artefact that implements
it and the evidence that demonstrates it.  A requirement with no evidence is a
gap and is listed as such.

| Requirement | Implementation | Evidence | Status |
| --- | --- | --- | --- |
| SR-1.1 placement order never worse | `pnp/optimization/placement.py` | `tests/test_optimization.py::test_optimize_placement_reduces_path` | verified |
| SR-1.2 type locality | `pnp/optimization/placement.py` | code review + report in CLI output | verified |
| SR-1.3 feeder assignment | `pnp/optimization/feeding.py` | `tests/test_optimization.py::test_optimize_feeders` | verified |
| SR-1.4 tray slot order | `pnp/optimization/feeding.py` | `tests/test_optimization.py::test_optimize_turntable` | verified |
| SR-1.5 baseline reported | `pnp/cli.py`, `asic/miniflow/placer.py` | CLI output, placement report | verified |
| SR-2.1 limit-respecting profiles | `pnp/planning/trajectory.py`, `rtl/motion/profile_gen.sv` | `test_plan_path`, `make hdl-synth` | verified |
| SR-2.2 profile ends on target | `pnp/planning/trajectory.py` | `tests/test_optimization.py` | verified |
| SR-2.3 no step drift | `rtl/motion/stepgen.sv` (DDA) | rtlsim `quad_decoder_motion`, review | verified |
| SR-2.4 combinational inhibit | `rtl/safety/limit_monitor.sv` | formal `limit_monitor_props` P3 | verified |
| SR-3.1 fiducial homography | `pnp/vision/pipeline.py` | unit tests, review | verified |
| SR-3.2 orientation measurement | `pnp/cv/orientation.py`, `rtl/vision/centroid_accel.sv` | unit tests | verified |
| SR-3.3 streaming moments | `rtl/vision/centroid_accel.sv` | synthesis report | verified |
| SR-4.1 CRC-protected frames | `rtl/comm/packet_if.sv`, `crc16_ccitt.sv` | rtlsim `spi_packet_link`, `crc_vectors` | verified |
| SR-4.2 length validation | `rtl/comm/packet_if.sv` | rtlsim `spi_packet_link` | verified |
| SR-4.3 link timeout | `rtl/comm/packet_if.sv` | code + `err_timeout` counter | verified (directed) |
| SR-4.4 watchdog window | `rtl/safety/watchdog_wwdg.sv` | formal `watchdog_props` | verified |
| SR-4.5 latching limits | `rtl/safety/limit_monitor.sv` | formal `limit_monitor_props` P1/P2 | verified |
| SR-4.6 telemetry rate limit | `rtl/top/pnp_core.sv` | review + synthesis | verified |
| SR-5.1 blocks elaborate and check | `rtl/**` | `make hdl-lint` | verified |
| SR-5.2 synthesis + area | `tools/hdl_flow.py` | `verification/reports/synth/summary.json` | verified |
| SR-5.3 divider arithmetic | `rtl/common/seq_div.sv` | formal `seq_div_props` P2 | verified |
| SR-5.4 encoder monotonicity | `rtl/motion/quad_decoder.sv` | formal `quad_decoder_props` P1 | verified |
| SR-5.5 GDS + sign-off | `asic/miniflow/*` | `asic/build/*_report.md` | implemented, closure open |
| SR-5.6 honest status reporting | `asic/miniflow/flow.py::_status` | `asic/build/summary.json` | verified |
| SR-6.1 offline install | `scripts/bootstrap.sh` | fresh-environment run | verified |
| SR-6.2 determinism | placer/router seeds | `test_placement_is_deterministic` | verified |
| SR-6.3 lint and typing | `pyproject.toml` | `make lint` | verified |
| SR-6.4 coverage does not regress | CI workflow | `coverage.xml` artefact | verified in CI |
| SR-6.5 typed public interfaces | `pnp/**`, `tools/**` | mypy configuration + review | partially verified |

## Gaps

| Gap | Reason | Plan |
| --- | --- | --- |
| SR-5.5 routing closure | the maze router is deliberately simple; high-fanout reset/clock nets need buffer insertion | add a reset/clock tree stage and a proper rip-up-and-reroute |
| Connectivity extraction | extracted connectivity still mismatches on `crc16_ccitt` while DRC is clean | second extraction pass with net-aware shape merging |
| SR-6.5 | mypy runs but is not enforced in CI (`continue-on-error`) | make it blocking once the remaining annotations land |
| Timing accuracy | no clock tree, no crosstalk, no derating | states its scope in every report |
