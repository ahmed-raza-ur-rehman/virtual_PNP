"""Thermal analysis and management."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ThermalNode:
    name: str
    temperature: float = 25.0
    power: float = 0.0
    thermal_mass: float = 1.0
    ambient: float = 25.0


class ThermalNetwork:
    def __init__(self):
        self.nodes: dict[str, ThermalNode] = {}
        self.resistances: dict[tuple[str, str], float] = {}
        self.capacitances: dict[str, float] = {}

    def add_node(self, node: ThermalNode):
        self.nodes[node.name] = node

    def add_resistance(self, a: str, b: str, r: float):
        self.resistances[(a, b)] = r
        self.resistances[(b, a)] = r

    def add_capacitance(self, node: str, c: float):
        self.capacitances[node] = c

    def steady_state(self) -> dict[str, float]:
        # solve linear system: power = (T - Tambient)/R
        # simplified iterative
        temps = {n: self.nodes[n].ambient for n in self.nodes}
        for _ in range(100):
            new_temps = dict(temps)
            for name, node in self.nodes.items():
                # sum heat flows
                flow = node.power
                for (a, b), r in self.resistances.items():
                    if a == name:
                        flow += (temps[b] - temps[a]) / r
                # update
                c = self.capacitances.get(name, 1.0)
                new_temps[name] = temps[name] + flow * 0.01 / c
            temps = new_temps
        for name in self.nodes:
            self.nodes[name].temperature = temps[name]
        return temps

    def transient(self, dt: float, steps: int) -> list[dict[str, float]]:
        temps = {n: self.nodes[n].ambient for n in self.nodes}
        history = []
        for _ in range(steps):
            new_temps = dict(temps)
            for name, node in self.nodes.items():
                flow = node.power
                for (a, b), r in self.resistances.items():
                    if a == name:
                        flow += (temps[b] - temps[a]) / r
                c = self.capacitances.get(name, 1.0)
                new_temps[name] = temps[name] + flow * dt / c
            temps = new_temps
            history.append(dict(temps))
        return history

    def max_temperature(self) -> float:
        return max(n.temperature for n in self.nodes.values()) if self.nodes else 0.0

    def thermal_resistance_junction_ambient(self, junction: str, ambient: str = "ambient") -> float:
        # find path
        return self.resistances.get((junction, ambient), 0.0)

    def report(self) -> str:
        temps = self.steady_state()
        lines = ["Thermal Analysis Report"]
        for name, t in temps.items():
            lines.append(f"  {name}: {t:.2f} C (power={self.nodes[name].power:.3f} W)")
        lines.append(f"  Max: {self.max_temperature():.2f} C")
        return "\n".join(lines)


class HeatSink:
    def __init__(self, area: float, fin_height: float, fin_thickness: float, num_fins: int, material_conductivity: float = 200.0):
        self.area = area
        self.fin_height = fin_height
        self.fin_thickness = fin_thickness
        self.num_fins = num_fins
        self.k = material_conductivity

    def thermal_resistance(self, airflow: float = 1.0) -> float:
        # simplified: R = 1/(h*A)
        h = 10 * (1 + airflow * 0.5)
        fin_area = self.num_fins * 2 * self.fin_height * 0.1  # approximate
        total_area = self.area + fin_area
        return 1.0 / (h * total_area + 1e-9)

    def pressure_drop(self, airflow: float) -> float:
        return 0.5 * 1.2 * airflow * airflow * 0.1

    def optimize_fin_spacing(self, target_r: float) -> float:
        return 0.01  # placeholder


class ThermalInterfaceMaterial:
    def __init__(self, conductivity: float, thickness: float, area: float):
        self.k = conductivity
        self.thickness = thickness
        self.area = area

    def resistance(self) -> float:
        return self.thickness / (self.k * self.area + 1e-9)
