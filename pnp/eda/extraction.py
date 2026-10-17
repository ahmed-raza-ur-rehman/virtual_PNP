"""Parasitic extraction: RC extraction from layout."""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Net:
    name: str
    segments: list[tuple[float, float, float, float]] = field(default_factory=list)
    capacitance: float = 0.0
    resistance: float = 0.0


class RCExtractor:
    def __init__(self, layer_params: dict[str, dict[str, float]] | None = None):
        self.layer_params = layer_params or {
            "metal1": {"sheet_r": 0.1, "cap_per_length": 0.2e-15, "fringe": 0.05e-15},
            "metal2": {"sheet_r": 0.08, "cap_per_length": 0.15e-15, "fringe": 0.04e-15},
            "metal3": {"sheet_r": 0.06, "cap_per_length": 0.12e-15, "fringe": 0.03e-15},
        }
        self.nets: dict[str, Net] = {}

    def add_net(self, net: Net):
        self.nets[net.name] = net

    def segment_length(self, seg: tuple[float, float, float, float]) -> float:
        x1, y1, x2, y2 = seg
        return math.hypot(x2 - x1, y2 - y1)

    def segment_resistance(self, seg, layer: str = "metal1", width: float = 1.0) -> float:
        length = self.segment_length(seg)
        params = self.layer_params.get(layer, self.layer_params["metal1"])
        return params["sheet_r"] * length / max(width, 1e-9)

    def segment_capacitance(self, seg, layer: str = "metal1", width: float = 1.0) -> float:
        length = self.segment_length(seg)
        params = self.layer_params.get(layer, self.layer_params["metal1"])
        area_cap = params["cap_per_length"] * length * width
        fringe = params["fringe"] * length
        return area_cap + fringe

    def coupling_capacitance(self, seg1, seg2, layer: str = "metal1") -> float:
        # simplified: inverse distance
        l1 = self.segment_length(seg1)
        l2 = self.segment_length(seg2)
        # distance between midpoints
        m1 = ((seg1[0]+seg1[2])/2, (seg1[1]+seg1[3])/2)
        m2 = ((seg2[0]+seg2[2])/2, (seg2[1]+seg2[3])/2)
        dist = math.hypot(m1[0]-m2[0], m1[1]-m2[1])
        if dist < 1e-9:
            return 0.0
        params = self.layer_params.get(layer, self.layer_params["metal1"])
        return params["cap_per_length"] * min(l1, l2) / dist * 0.1

    def extract_net(self, net: Net, layer: str = "metal1", width: float = 1.0) -> dict[str, float]:
        r = 0.0
        c = 0.0
        for seg in net.segments:
            r += self.segment_resistance(seg, layer, width)
            c += self.segment_capacitance(seg, layer, width)
        net.resistance = r
        net.capacitance = c
        return {"resistance": r, "capacitance": c, "rc_delay": r * c}

    def extract_all(self, layer: str = "metal1", width: float = 1.0) -> dict[str, dict[str, float]]:
        out = {}
        for name, net in self.nets.items():
            out[name] = self.extract_net(net, layer, width)
        return out

    def pi_model(self, net: Net) -> dict[str, float]:
        r = net.resistance
        c = net.capacitance
        return {"r": r, "c1": c / 2, "c2": c / 2, "tau": 0.69 * r * c / 2}

    def elmore_delay(self, segments: list[tuple[float, float, float, float]], caps: list[float]) -> float:
        # Elmore delay for an RC chain
        total = 0.0
        cum_r = 0.0
        for i, (seg, cap) in enumerate(zip(segments, caps)):
            r = self.segment_resistance(seg)
            cum_r += r
            total += cum_r * cap
        return total

    def report(self) -> str:
        lines = ["RC Extraction Report"]
        lines.append(f"  Nets: {len(self.nets)}")
        for name, net in self.nets.items():
            lines.append(f"    {name}: R={net.resistance:.3f} C={net.capacitance:.3e} tau={net.resistance*net.capacitance:.3e}")
        return "\n".join(lines)


class SPEFWriter:
    """Write Standard Parasitic Exchange Format."""
    def __init__(self):
        self.lines: list[str] = []

    def header(self, design: str = "top"):
        self.lines.append("*SPEF \"IEEE 1481-1999\"")
        self.lines.append(f"*DESIGN \"{design}\"")
        self.lines.append("*DATE \"2026\"")
        self.lines.append("*VENDOR \"virtual_pnp\"")
        self.lines.append("*PROGRAM \"rc_extract\"")
        self.lines.append("*VERSION \"1.0\"")

    def write_net(self, net: Net):
        self.lines.append(f"*D_NET {net.name} {net.capacitance:.6e}")
        self.lines.append("*CONN")
        self.lines.append("*CAP")
        self.lines.append(f"1 {net.name} {net.capacitance:.6e}")
        self.lines.append("*RES")
        self.lines.append(f"1 {net.name} {net.resistance:.6e}")
        self.lines.append("*END")

    def dump(self, nets: list[Net]) -> str:
        self.header()
        for n in nets:
            self.write_net(n)
        return "\n".join(self.lines)

    def write_file(self, path: str, nets: list[Net]):
        content = self.dump(nets)
        with open(path, "w") as f:
            f.write(content)
        return path
