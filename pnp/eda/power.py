"""Power analysis: dynamic, static (leakage), short-circuit."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class PowerCell:
    name: str
    cell_type: str
    capacitance: float = 1e-15  # F
    switching_activity: float = 0.5
    leakage_current: float = 1e-9  # A
    short_circuit_factor: float = 0.1
    vdd: float = 1.0
    frequency: float = 1e9


class PowerAnalyzer:
    def __init__(self, vdd: float = 1.0, temperature: float = 25.0):
        self.vdd = vdd
        self.temperature = temperature
        self.cells: list[PowerCell] = []
        self.nets: list[dict[str, Any]] = []

    def add_cell(self, cell: PowerCell):
        self.cells.append(cell)

    def dynamic_power(self, cell: PowerCell) -> float:
        # P = 0.5 * C * V^2 * f * alpha
        return 0.5 * cell.capacitance * cell.vdd**2 * cell.frequency * cell.switching_activity

    def leakage_power(self, cell: PowerCell) -> float:
        # P = I_leak * V
        temp_factor = 1.0 + 0.02 * (self.temperature - 25.0)
        return cell.leakage_current * cell.vdd * temp_factor

    def short_circuit_power(self, cell: PowerCell) -> float:
        return self.dynamic_power(cell) * cell.short_circuit_factor

    def total_cell_power(self, cell: PowerCell) -> dict[str, float]:
        dyn = self.dynamic_power(cell)
        leak = self.leakage_power(cell)
        sc = self.short_circuit_power(cell)
        return {"dynamic": dyn, "leakage": leak, "short_circuit": sc, "total": dyn + leak + sc}

    def analyze(self) -> dict[str, Any]:
        totals = {"dynamic": 0.0, "leakage": 0.0, "short_circuit": 0.0, "total": 0.0}
        per_cell = []
        for c in self.cells:
            p = self.total_cell_power(c)
            per_cell.append({"name": c.name, "type": c.cell_type, **p})
            for k in totals:
                totals[k] += p[k]
        # net switching power
        net_power = 0.0
        for n in self.nets:
            cap = n.get("capacitance", 0.0)
            freq = n.get("frequency", 1e9)
            act = n.get("activity", 0.5)
            net_power += 0.5 * cap * self.vdd**2 * freq * act
        totals["net_switching"] = net_power
        totals["grand_total"] = totals["total"] + net_power
        return {"cells": per_cell, "totals": totals, "num_cells": len(self.cells)}

    def report(self) -> str:
        r = self.analyze()
        t = r["totals"]
        lines = ["Power Analysis Report", f"  Cells: {r['num_cells']}"]
        lines.append(f"  Dynamic: {t['dynamic']*1e6:.3f} uW")
        lines.append(f"  Leakage: {t['leakage']*1e6:.3f} uW")
        lines.append(f"  Short-circuit: {t['short_circuit']*1e6:.3f} uW")
        lines.append(f"  Net switching: {t.get('net_switching',0)*1e6:.3f} uW")
        lines.append(f"  Total: {t['grand_total']*1e6:.3f} uW")
        # top consumers
        cells = sorted(r["cells"], key=lambda c: c["total"], reverse=True)[:5]
        lines.append("  Top consumers:")
        for c in cells:
            lines.append(f"    {c['name']} ({c['type']}): {c['total']*1e6:.3f} uW")
        return "\n".join(lines)

    def voltage_scaling(self, new_vdd: float) -> dict[str, float]:
        # dynamic scales with V^2, leakage scales linearly
        old = self.analyze()["totals"]
        ratio_dyn = (new_vdd / self.vdd) ** 2
        ratio_leak = new_vdd / self.vdd
        return {
            "dynamic": old["dynamic"] * ratio_dyn,
            "leakage": old["leakage"] * ratio_leak,
            "total": old["dynamic"] * ratio_dyn + old["leakage"] * ratio_leak,
        }

    def thermal_analysis(self, ambient: float = 25.0, theta_ja: float = 50.0) -> dict[str, float]:
        power = self.analyze()["totals"]["grand_total"]
        delta_t = power * theta_ja
        junction = ambient + delta_t
        return {"ambient": ambient, "junction": junction, "delta": delta_t, "theta_ja": theta_ja}


class PowerGrid:
    """Power distribution network (PDN) analysis."""

    def __init__(self, width: int, height: int, pitch: float = 10.0):
        self.width = width
        self.height = height
        self.pitch = pitch
        self.vdd_nodes: list[tuple[float, float]] = []
        self.gnd_nodes: list[tuple[float, float]] = []
        self.ir_drops: dict[tuple[float, float], float] = {}

    def build_mesh(self):
        x = 0.0
        while x <= self.width:
            y = 0.0
            while y <= self.height:
                self.vdd_nodes.append((x, y))
                y += self.pitch
            x += self.pitch

    def compute_ir_drop(self, current_map: dict[tuple[float, float], float], sheet_resistance: float = 0.01):
        for node, current in current_map.items():
            # simple: IR drop proportional to distance to nearest VDD tap
            if self.vdd_nodes:
                nearest = min(self.vdd_nodes, key=lambda v: (v[0]-node[0])**2 + (v[1]-node[1])**2)
                dist = math.hypot(nearest[0]-node[0], nearest[1]-node[1])
                self.ir_drops[node] = current * sheet_resistance * dist
            else:
                self.ir_drops[node] = 0.0
        return self.ir_drops

    def worst_ir_drop(self) -> float:
        return max(self.ir_drops.values()) if self.ir_drops else 0.0

    def electromigration_check(self, current_density: float, limit: float = 1e6) -> bool:
        return current_density <= limit
