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
