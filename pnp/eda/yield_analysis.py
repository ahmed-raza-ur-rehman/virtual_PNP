"""Yield analysis and design for manufacturability."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class DefectDensity:
    layer: str
    defects_per_cm2: float
    critical_area_factor: float = 1.0


class YieldModel:
    def __init__(self):
        self.defects: list[DefectDensity] = []
        self.die_area_cm2: float = 1.0

    def add_defect(self, d: DefectDensity):
        self.defects.append(d)

    def poisson_yield(self, defect_density: float, area: float) -> float:
        return math.exp(-defect_density * area)

    def murphy_yield(self, defect_density: float, area: float) -> float:
        lam = defect_density * area
        if lam == 0:
            return 1.0
        return ((1 - math.exp(-lam)) / lam) ** 2

    def seeds_yield(self, defect_density: float, area: float) -> float:
        lam = defect_density * area
        return (1 + lam / 4) ** (-4) if lam >= 0 else 1.0

    def total_defect_density(self) -> float:
        return sum(d.defects_per_cm2 * d.critical_area_factor for d in self.defects)

    def compute_yield(self, model: str = "poisson") -> float:
        dd = self.total_defect_density()
        if model == "poisson":
            return self.poisson_yield(dd, self.die_area_cm2)
        if model == "murphy":
            return self.murphy_yield(dd, self.die_area_cm2)
        if model == "seeds":
            return self.seeds_yield(dd, self.die_area_cm2)
        return self.poisson_yield(dd, self.die_area_cm2)

    def yield_vs_area(self, areas: list[float]) -> list[float]:
        dd = self.total_defect_density()
        return [self.poisson_yield(dd, a) for a in areas]

    def dpm(self) -> float:
        # defects per million
        return (1 - self.compute_yield()) * 1e6

    def good_dies_per_wafer(self, wafer_diameter_mm: float = 300, edge_exclusion_mm: float = 3) -> float:
        wafer_area = math.pi * ((wafer_diameter_mm / 2 - edge_exclusion_mm) ** 2)
        die_area_mm2 = self.die_area_cm2 * 100
        dies_per_wafer = wafer_area / die_area_mm2
        return dies_per_wafer * self.compute_yield()

    def report(self) -> str:
        lines = ["Yield Analysis Report"]
        lines.append(f"  Die area: {self.die_area_cm2} cm2")
        lines.append(f"  Total defect density: {self.total_defect_density():.4f} /cm2")
        lines.append(f"  Poisson yield: {self.poisson_yield(self.total_defect_density(), self.die_area_cm2)*100:.2f}%")
        lines.append(f"  Murphy yield: {self.murphy_yield(self.total_defect_density(), self.die_area_cm2)*100:.2f}%")
        lines.append(f"  DPM: {self.dpm():.1f}")
        lines.append(f"  Good dies/wafer (300mm): {self.good_dies_per_wafer():.0f}")
        return "\n".join(lines)


class CriticalAreaAnalysis:
    def __init__(self, layout_size: tuple[float, float]):
        self.layout_size = layout_size
        self.critical_areas: dict[str, float] = {}

    def compute_critical_area(self, defect_radius: float, shape_area: float) -> float:
        # simplified: critical area = shape_area + perimeter * r + pi * r^2
        return shape_area + defect_radius * 10 + math.pi * defect_radius * defect_radius

    def add_shape(self, name: str, area: float, perimeter: float, defect_radius: float = 0.1):
        ca = area + perimeter * defect_radius + math.pi * defect_radius * defect_radius
        self.critical_areas[name] = ca

    def total_critical_area(self) -> float:
        return sum(self.critical_areas.values())

    def defect_sensitivity(self, defect_radius: float) -> float:
        return self.total_critical_area() / (self.layout_size[0] * self.layout_size[1])
