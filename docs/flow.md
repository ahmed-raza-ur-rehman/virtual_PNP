# Software/Hardware/Firmware Flow

1. User designs PCB + components in GUI.
2. Placement optimizer orders components.
3. Path planner generates S-curve trajectories.
4. Motion optimizer validates collision-free paths.
5. CV module verifies orientation/alignment.
6. Export to firmware: G-code-like or binary trajectory.
7. MCU streams trajectory to FPGA over SPI.
8. FPGA executes motion with encoder feedback.
9. Telemetry returned to GUI for monitoring/tweaking.
