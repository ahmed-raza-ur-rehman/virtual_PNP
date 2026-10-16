# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Repository governance: MIT licence, contributing guide, security policy,
  conventional-commit pre-commit hooks, issue/PR templates, Dependabot.

## [2.0.0] - 2026-10-15

### Added
- **Core domain model** (`pnp/core`): pydantic v2 machine, feeder, component and
  placement models with coordinate-system conventions, kinematics helpers and
  a workspace checker.
- **Placement optimisation** (`pnp/optimization`): type-block sequencing,
  nearest-neighbour construction and 2-opt refinement; feeder-slot assignment
  by placement-density projection; circular tray (turntable) slot ordering.
- **Trajectory planning** (`pnp/planning`): jerk-limited S-curve and trapezoidal
  profiles, multi-segment path planner, segment/obstacle collision test.
- **Vision** (`pnp/vision`, `pnp/cv`): camera calibration, fiducial detection,
  homography estimation, principal-axis orientation measurement and machine
  affine calibration.
- **Machine learning** (`pnp/ml`, `pnp/models`): orientation-classification CNN,
  dataset split helpers and losses.
- **Machine simulation** (`pnp/sim`): discrete-event digital twin with per-axis
  motion, feeder sequencing and throughput measurement.
- **Interfaces**: Typer CLI (`vpnp`), FastAPI service and a dependency-free web
  GUI (`python -m pnp.webgui`).
- **Firmware**: STM32 HAL + FreeRTOS task set, ESP32, RP2040 and AVR entry
  points; shared header with the host-side motion contract.
- **HDL**: synthesizable Verilog for PWM, quadrature encoder, motion controller,
  SPI slave, UART transmitter, watchdog and trajectory buffer plus a top level.
- **Verification**: layered SystemVerilog testbench, protocol and safety
  assertions, functional coverage model, UVM agent skeleton, cocotb test and a
  written verification & validation plan.
- **ASIC flow**: OpenLane configuration, Yosys synthesis script and constraints
  for an RTL-to-GDSII path.
- **Documentation**: architecture, software/hardware/firmware flow, trade-off
  analysis, interface specifications, BOM and machine datums.
- **Tooling**: GitHub Actions CI for software, HDL and firmware, Makefile entry
  points, bootstrap script, ruff/pytest configuration.
- **Web simulator**: enhanced Three.js machine simulator (`index.html`,
  `b.html`) with machine profiles, optimisation controls and physics; the
  original Essemtec-style prototype is preserved as `c.html`.
- **Multi-language kernels**: C++ optimiser/planner with CTest, Rust crate,
  Go service package, hand-written x86-64 assembly math routines.

[Unreleased]: https://github.com/ahmed-raza-ur-rehman/virtual_PNP/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/ahmed-raza-ur-rehman/virtual_PNP/releases/tag/v2.0.0

## [2.1.0] - 2026-10-15

### Added
- **RTL subsystem** (`rtl/`): SystemVerilog/V2001-synthesizable control core with
  a compiled-in interface contract (`rtl/common/pnp_defs.svh`): jerk-limited
  `profile_gen`, `quad_decoder` with debounce and index latch, `stepgen` DDA,
  `pid_axis` with anti-windup, `seq_div`, `crc16_ccitt`, `uart_tx`/`uart_rx`,
  `spi_slave`, `packet_if` (framed command parser), `csr_bank`, window watchdog,
  latching `limit_monitor`, streaming `centroid_accel` and the `pnp_core` top.
- **Formal verification** (`verification/formal/`): SymbiYosys tasks proving
  divider arithmetic and protocol, watchdog window semantics, limit-monitor
  latching and encoder monoticity, with non-vacuity covers.
- **HDL flow driver** (`tools/hdl_flow.py`) plus `make hdl-lint|hdl-synth|formal`
  and repository tool shims (`tools/bin`) so the open-source EDA backend runs
  from pip installs alone.

### Fixed
- `seq_div` implemented repeated subtraction instead of restoring division and
  produced a saturated quotient for any dividend >= W*divisor.  Found by formal
  property `seq_div_props` P2 (`quotient*divisor + remainder == dividend`).
  The zero-divisor path now takes the same latency as a normal division.
- `watchdog_wwdg` did not restart the window when a fault was acknowledged,
  leaving the counter beyond `WIN_HIGH` with the reset request cleared.
- `watchdog_wwdg` raised the trip one cycle after the counter passed the upper
  window bound, making the effective window one cycle longer than specified.
- `limit_monitor` registered `motion_inhibit`, adding a clock of latency to the
  emergency-stop path; it is now combinational behind the debounce filter.

## [2.1.0] - 2026-10-15

### Added
- **RTL subsystem** (`rtl/`): jerk-limited `profile_gen`, quadrature
  `quad_decoder`, `stepgen` DDA, `pid_axis` with anti-windup, `seq_div`, CRC-16
  framing, UART/SPI links, `packet_if` command parser, `csr_bank`, window
  watchdog, latching `limit_monitor`, streaming `centroid_accel` and the
  `pnp_core` top level.
- **Formal verification** (`verification/formal/`): SymbiYosys tasks with
  reachability covers proving divider arithmetic, watchdog windows, limit
  latching and encoder monotonicity.  `make formal`.
- **Netlist simulator** (`tools/rtlsim/`): yosys JSON reader, cycle-accurate
  gate/DFF evaluator, VCD writer and six functional testbenches driven against
  the synthesised gate netlists.  `make rtl-sim`.
- **RTL-to-GDSII mini-flow** (`asic/miniflow/`): netlist mapping, row-based
  placement with legal rotation moves, five-layer maze routing, GDSII writer and
  reader, DRC, layout connectivity extraction and RC timing.  `make asic`.
- Documentation set: `docs/SRS.md`, `docs/ICD.md`, `docs/evidence.md`,
  `docs/TRACEABILITY.md`, `docs/asic_miniflow.md`, plus a rewritten `README.md`.

### Fixed
- `seq_div` computed repeated subtractions instead of restoring division.
- `watchdog_wwdg` did not restart its window on fault acknowledgement and
  tripped one cycle late; `limit_monitor` delayed the stop path by a clock.
- `packet_if` folded the second sync byte and both CRC bytes into the running
  CRC, so every well-formed frame failed verification.
- Library cells could place two pins on one routing column and the placer could
  overlap cells; the layout DRC drew wires a full pitch wide.

### Changed
- Repository layout: `rtl/` is now the canonical RTL root, `firmware/fpga`
  configuration points at it, and `synthesis/build/` is generated rather than
  tracked.
