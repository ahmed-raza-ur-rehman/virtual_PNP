# Software / System Requirements Specification (SRS)

**Document:** VP-SRS-001 · **Version:** 2.1 · **Status:** released
**Scope:** the virtual place-and-place platform: offline simulator, optimisers,
control software, firmware, RTL and the RTL-to-GDSII flow.

Requirement identifiers (`SR-*`) are the ones referenced by the traceability
matrix (`docs/TRACEABILITY.md`), the verification report and the issue
templates.  Every requirement is stated so that it can be *verified*: it names
the observable, the condition and the limit.

---

## 1. Operating context

| Item | Value |
| --- | --- |
| Machine class | gantry SMD pick-and-place, 3 axes (X, Y, Z) + rotational nozzle |
| Board size | up to 500 x 400 mm |
| Component classes | 0402…1206 chip, LED, SOT/SOIC/QFN, BGA ≥ 0.5 mm pitch |
| Feeder bank | up to 64 tape feeders, up to 4 trays, 1 circular tray option |
| Host links | SPI (real-time) and UART (telemetry/commands) |
| Control rate | 1 kHz position loop; 10 - 100 MHz logic clock |

## 2. Functional requirements

### 2.1 Placement planning

| ID | Requirement | Verification |
| --- | --- | --- |
| SR-1.1 | The system shall produce a placement order that never increases the
travelled distance relative to the input order. | `tests/test_optimization.py::test_optimize_placement_reduces_path` |
| SR-1.2 | Placement order shall respect component-type locality (no interleaving
of types beyond the grouping stage). | `pnp/optimization/placement.py` + review |
| SR-1.3 | Feeder slots shall be assigned to minimise the projection of placement
coordinates onto the feeder axis. | `tests/test_optimization.py::test_optimize_feeders` |
| SR-1.4 | Circular tray slots shall be assigned in angular order of the placement
density. | `tests/test_optimization.py::test_optimize_turntable` |
| SR-1.5 | The optimiser shall expose the baseline it improved and by how much. | `pnp/cli.py optimize` output |

### 2.2 Motion

| ID | Requirement | Verification |
| --- | --- | --- |
| SR-2.1 | Every motion segment shall respect the configured velocity,
acceleration and jerk limits. | `tests/test_optimization.py::test_plan_path`, RTL `profile_gen` |
| SR-2.2 | A motion profile shall end on its target within one position LSB. | rtlsim `quad_decoder_motion`, `pnp/planning` tests |
| SR-2.3 | The step generator shall not accumulate position error: the average
step rate over any window shall equal the commanded velocity. | RTL `stepgen` (DDA carry), review |
| SR-2.4 | Motion shall be inhibited combinationally when a limit channel is
asserted. | formal `limit_monitor_props` P3 |

### 2.3 Vision

| ID | Requirement | Verification |
| --- | --- | --- |
| SR-3.1 | Board coordinates shall be computed from at least three fiducials by
homography, tolerating one outlier. | `pnp/vision/pipeline.py::estimate_homography` |
| SR-3.2 | Component orientation shall be measurable to ±2° for parts with a
principal axis. | `pnp/cv/orientation.py` |
| SR-3.3 | Centroid and second moments shall be computable in the pixel stream
without a frame buffer. | RTL `centroid_accel`, synthesis report |

### 2.4 Communication and safety

| ID | Requirement | Verification |
| --- | --- | --- |
| SR-4.1 | Command frames shall be CRC-16/CCITT protected; a corrupted frame shall
be rejected and counted. | rtlsim `spi_packet_link`, formal `packet_if` |
| SR-4.2 | A frame whose length field is outside 1…8 shall be rejected. | rtlsim `spi_packet_link` |
| SR-4.3 | A stalled host link shall raise a timeout within a bounded number of
clocks. | RTL `packet_if` timeout counter |
| SR-4.4 | A watchdog kick that is too early or too late shall raise a latched
fault; the window shall restart only on an explicit acknowledgement. | formal `watchdog_props` |
| SR-4.5 | A limit or emergency-stop assertion shall latch until cleared while all
channels read safe. | formal `limit_monitor_props` P1/P2 |
| SR-4.6 | Telemetry shall be rate limited so that it cannot starve the control
loop. | RTL `pnp_core` `TELEM_DIV` divider |

### 2.5 Backend and flow

| ID | Requirement | Verification |
| --- | --- | --- |
| SR-5.1 | The RTL shall elaborate and pass `check` for every block. | `make hdl-lint` |
| SR-5.2 | Every block shall synthesise to a gate netlist and report area. | `make hdl-synth` |
| SR-5.3 | The divider shall satisfy `quotient*divisor + remainder == dividend`
for all operands. | formal `seq_div_props` P2 |
| SR-5.4 | The encoder counter shall move by at most one count per clock. | formal `quad_decoder_props` P1 |
| SR-5.5 | The flow shall emit GDSII for a placed and routed block and check it
for DRC, connectivity and timing. | `make asic` + `asic/build/*_report.md` |
| SR-5.6 | Any stage that does not close shall be reported as such, with the
failing items enumerated. | `asic/miniflow/flow.py::_status` |

## 3. Non-functional requirements

| ID | Requirement | Verification |
| --- | --- | --- |
| SR-6.1 | The software stack shall install and run offline from PyPI packages
only, with no OS packages required. | `scripts/bootstrap.sh` |
| SR-6.2 | Deterministic behaviour: optimisers, placer and simulator shall be
seed-reproducible. | `tests/test_asic_flow.py::test_placement_is_deterministic` |
| SR-6.3 | Static analysis (ruff) and typing (mypy config) shall be clean for
`pnp`, `tools` and `tests`. | `make lint` |
| SR-6.4 | Test coverage of the touched modules shall not decrease. | CI coverage artefact |
| SR-6.5 | Public interfaces shall be typed and documented. | review + `docs/ICD.md` |

## 4. Out of scope (explicit)

* Transistor-level LVS of the standard-cell library (the flow performs
  connectivity extraction, not device extraction).
* Antenna, density and latch-up DRC rules.
* Clock-tree synthesis and scan insertion; the flow documents the resulting
  limitation on high-fanout nets.
* Real-machine acceptance testing; the platform is a virtual machine plus the
  control logic and layout it would drive.
