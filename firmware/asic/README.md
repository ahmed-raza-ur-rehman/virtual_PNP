# ASIC version

The ASIC implementation reuses the FPGA RTL in `firmware/fpga/rtl/` and is
targeted at a 180nm/130nm mixed-signal process. Key differences vs FPGA:

- Clock gating on idle axes to reduce dynamic power.
- Analog front-end: integrated ADC for current sensing, DAC for motor drive.
- Hardened memory (SRAM) for trajectory buffers.
- DFT (scan) inserted for testability.

Synthesis flow: Yosys -> OpenROAD/ORFS for open-source, or vendor tools.
