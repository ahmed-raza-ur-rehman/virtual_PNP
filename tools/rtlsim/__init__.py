"""Cycle-accurate simulator for Yosys gate-level netlists.

The platform needs a simulator that runs anywhere: no Verilator, no Icarus, no
commercial licence.  This package reads the JSON netlist emitted by
``yosys write_json`` (the same artefact the ASIC flow consumes) and evaluates
it cycle by cycle in Python.  Because it consumes the *netlist* rather than the
source, a testbench run here proves something about the logic that was actually
synthesised, not just about the RTL text.
"""

from .netlist import Design, NetlistError, load_design
from .sim import Simulation, SimError
from .vcd import VCDWriter

__all__ = [
    "Design",
    "NetlistError",
    "Simulation",
    "SimError",
    "VCDWriter",
    "load_design",
]
