"""RTL synthesis engine (Python-based, educational)."""
from __future__ import annotations

import re
from typing import Any


class SynthesisEngine:
    """Parses Verilog/SystemVerilog and produces a gate-level netlist."""

    def __init__(self):
        self.modules: dict[str, Any] = {}
        self.netlist: dict[str, Any] = {}

    def parse_verilog(self, source: str) -> dict[str, Any]:
        """Parse a Verilog module into an AST-like dict."""
        mod_match = re.search(r"module\s+(\w+)\s*\(([^)]*)\)\s*;", source)
        if not mod_match:
            raise ValueError("No module found")
        name = mod_match.group(1)
        ports = [p.strip() for p in mod_match.group(2).split(",")]
        # find always blocks
        always_blocks = re.findall(r"always\s*@\([^)]*\)\s*begin(.*?)end", source, re.DOTALL)
        # find assign statements
        assigns = re.findall(r"assign\s+(\w+)\s*=\s*(.+?);", source)
        # find reg/wire declarations
        regs = re.findall(r"reg\s+(?:\[\d+:\d+\]\s+)?(\w+)", source)
        wires = re.findall(r"wire\s+(?:\[\d+:\d+\]\s+)?(\w+)", source)
        return {
            "name": name,
            "ports": ports,
            "always_blocks": always_blocks,
            "assigns": assigns,
            "regs": regs,
            "wires": wires,
        }

    def synthesize(self, ast: dict[str, Any]) -> dict[str, Any]:
        """Convert AST to gate-level netlist."""
        netlist = {"module": ast["name"], "gates": [], "nets": [], "ports": ast["ports"]}
        # Convert assigns to gates
        for lhs, rhs in ast["assigns"]:
            netlist["gates"].append({"type": "BUF", "output": lhs, "inputs": [rhs.strip()]})
        # Convert always blocks to flip-flops
        for block in ast["always_blocks"]:
            if "posedge" in block or "negedge" in block:
                # extract register assignments
                assigns = re.findall(r"(\w+)\s*<=\s*(.+?);", block)
                for reg, expr in assigns:
                    netlist["gates"].append({"type": "DFF", "output": reg, "inputs": [expr.strip()]})
        return netlist

    def optimize(self, netlist: dict[str, Any]) -> dict[str, Any]:
        """Optimize netlist: remove unused gates, merge buffers."""
        used = set()
        for g in netlist["gates"]:
            for inp in g.get("inputs", []):
                used.add(inp)
        # remove gates whose output is not used
        new_gates = []
        for g in netlist["gates"]:
            if g["output"] in used or g["output"] in netlist["ports"]:
                new_gates.append(g)
        netlist["gates"] = new_gates
        return netlist

    def technology_map(self, netlist: dict[str, Any], library: dict[str, Any]) -> dict[str, Any]:
        """Map generic gates to standard cells."""
        mapped = {"module": netlist["module"], "cells": [], "ports": netlist["ports"]}
        for g in netlist["gates"]:
            cell_type = "INV_X1" if g["type"] == "BUF" else "DFF_X1"
            mapped["cells"].append({"type": cell_type, "name": g["output"], "pins": g})
        return mapped

    def report(self, netlist: dict[str, Any]) -> str:
        lines = [f"Module: {netlist['module']}", f"Ports: {len(netlist['ports'])}"]
        lines.append(f"Gates: {len(netlist.get('gates', []))}")
        lines.append(f"Cells: {len(netlist.get('cells', []))}")
        return "\n".join(lines)
