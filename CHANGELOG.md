# Changelog

All notable changes to this project are documented here.

## [2.0.0] - 2026-10-16
### Added
- Multi-language implementations (Python, C++, Rust, Go, Assembly).
- Multi-MCU firmware (STM32, ESP32, RP2040, AVR).
- Expanded FPGA RTL (UART, watchdog, trajectory buffer, PID, quadrature).
- ASIC RTL-to-GDSII flow (OpenLane/Yosys/OpenROAD).
- UVM verification agent, SVA, functional coverage, cocotb.
- Professional Python package: core models, optimization, planning, vision, ML, API, CLI.
- Test suite, CI workflow, pre-commit, Dockerfile.
- Logging, configuration, exceptions, run history.
### Changed
- Refactored optimization algorithms with type hints and tests.
### Fixed
- Import hygiene and lint (ruff clean).
