"""Automatic Test Pattern Generation (ATPG)."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


@dataclass
class Fault:
    name: str
    type: str  # stuck-at-0, stuck-at-1, bridging, transition
    location: str
    detected: bool = False


class ATPGEngine:
    def __init__(self, netlist: dict[str, Any] | None = None):
        self.netlist = netlist or {}
        self.faults: list[Fault] = []
        self.test_patterns: list[dict[str, Any]] = []
        self.coverage: float = 0.0

    def generate_fault_list(self) -> list[Fault]:
        faults = []
        for gate in self.netlist.get("gates", []):
            out = gate.get("output", "")
            faults.append(Fault(name=f"{out}_SA0", type="stuck-at-0", location=out))
            faults.append(Fault(name=f"{out}_SA1", type="stuck-at-1", location=out))
        for p in self.netlist.get("ports", []):
            faults.append(Fault(name=f"{p}_SA0", type="stuck-at-0", location=p))
            faults.append(Fault(name=f"{p}_SA1", type="stuck-at-1", location=p))
        self.faults = faults
        return faults

    def random_pattern(self, inputs: list[str]) -> dict[str, int]:
        return {i: random.randint(0, 1) for i in inputs}

    def fault_simulate(self, pattern: dict[str, int], fault: Fault) -> bool:
        # simplified: a fault is detected if pattern activates it and propagates
        # activation: for SA0, need input 1; for SA1, need input 0
        val = pattern.get(fault.location, 0)
        if fault.type == "stuck-at-0":
            activated = val == 1
        else:
            activated = val == 0
        # propagation probability ~0.5
        return activated and random.random() > 0.3

    def generate_patterns(self, num_patterns: int = 100, inputs: list[str] | None = None) -> list[dict[str, Any]]:
        inputs = inputs or self.netlist.get("ports", [])
        if not self.faults:
            self.generate_fault_list()
        patterns = []
        for _ in range(num_patterns):
            pat = self.random_pattern(inputs)
            detected = []
            for f in self.faults:
                if not f.detected and self.fault_simulate(pat, f):
                    f.detected = True
                    detected.append(f.name)
            if detected:
                patterns.append({"pattern": pat, "detected": detected})
        self.test_patterns = patterns
        self._update_coverage()
        return patterns

    def _update_coverage(self):
        if not self.faults:
            self.coverage = 0.0
            return
        detected = sum(1 for f in self.faults if f.detected)
        self.coverage = detected / len(self.faults)

    def podem(self, fault: Fault, inputs: list[str]) -> dict[str, int] | None:
        # simplified PODEM: try random search
        for _ in range(1000):
            pat = self.random_pattern(inputs)
            if self.fault_simulate(pat, fault):
                return pat
        return None

    def report(self) -> str:
        self._update_coverage()
        lines = ["ATPG Report"]
        lines.append(f"  Faults: {len(self.faults)}")
        lines.append(f"  Detected: {sum(1 for f in self.faults if f.detected)}")
        lines.append(f"  Coverage: {self.coverage*100:.1f}%")
        lines.append(f"  Test patterns: {len(self.test_patterns)}")
        return "\n".join(lines)

    def fault_coverage_by_type(self) -> dict[str, float]:
        out = {}
        for ftype in ("stuck-at-0", "stuck-at-1", "bridging", "transition"):
            fs = [f for f in self.faults if f.type == ftype]
            if fs:
                out[ftype] = sum(1 for f in fs if f.detected) / len(fs)
        return out
