# Virtual SMD Pick & Place Machine

Professional virtual SMD pick-and-place platform: design, simulate, optimize and
tweak before ordering hardware. Includes 3D simulator, Python ML/CV algorithms,
optimizers, S-curve path planning, motion optimization, and firmware for STM32,
FPGA (Verilog/SystemVerilog) and ASIC.

## Quick start

### Web 3D simulator
Open `index.html` (or `b.html`) in a browser (uses `three.min.js`).

### Python algorithms / GUI
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pnp.webgui   # web GUI + algorithm endpoints
.venv/bin/python -m pnp.gui.main_window  # PyQt5 desktop (needs libGL)
```

### Tests
```bash
.venv/bin/python -c "import pnp; from pnp.algorithms.placement_optimizer import optimize_placement; print('ok')"
```

## Structure
- `pnp/` Python package (algorithms, cv, models, sim, gui, webgui)
- `firmware/stm32/` STM32 firmware (C)
- `firmware/fpga/` Verilog RTL + testbenches + constraints
- `firmware/asic/` ASIC notes + synthesis script
- `docs/` architecture, flow, tradeoffs, specs
- `hardware/` BOM

## Features
- Multiple machine profiles (speed/accuracy/multi-head)
- Placement sequence optimization (nearest-neighbor + 2-opt + type grouping)
- Feeder and circular-tray (turntable) order optimization
- S-curve / trapezoidal path planning with jerk limits
- Motion optimization and collision checking
- CV orientation detection and fiducial alignment
- Lightweight CNN for orientation classification

## Multi-language implementations
- Python: `pnp/` (optimization, planning, vision, ML, API, CLI)
- C++: `cpp/` (high-performance optimization/planning)
- Rust: `rust/` (memory-safe motion planning)
- Go: `go/` (concurrent services)
- Assembly: `asm/` (x86-64 fast math)
- C firmware: `firmware/` (STM32, ESP32, RP2040, AVR)
- HDL: `firmware/fpga/` (Verilog RTL) + `verification/` (SV/UVM/cocotb)
- ASIC: `firmware/asic/` + `synthesis/` (RTL-to-GDSII flow)
