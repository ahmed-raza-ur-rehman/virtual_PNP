# System Architecture

## Layers
1. **Simulation / GUI (Python + Web)**: 3D visualization, algorithms, optimization.
2. **Firmware (STM32)**: real-time motion control, vacuum, sensors.
3. **FPGA**: high-speed deterministic motion, PWM, encoder counting, SPI to MCU.
4. **ASIC**: production silicon, lowest power/cost.

## Data flow
GUI -> trajectory (waypoints) -> MCU -> FPGA (SPI) -> motor drivers -> mechanics.
Feedback: encoders -> FPGA -> MCU -> GUI (status/telemetry).
