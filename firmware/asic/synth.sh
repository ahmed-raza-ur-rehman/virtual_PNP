#!/bin/bash
# Example open-source synthesis flow
yosys -p "read_verilog firmware/fpga/rtl/*.v; synth -top top; write_verilog asic_netlist.v"
echo "Netlist written to asic_netlist.v"
