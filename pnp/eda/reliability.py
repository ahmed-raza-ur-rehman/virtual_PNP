"""Reliability analysis: MTTF, FIT, electromigration, TDDB, HCI."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class ReliabilityModel:
    temperature: float = 25.0  # Celsius
    voltage: float = 1.0
    activation_energy: float = 0.7  # eV
    boltzmann: float = 8.617e-5  # eV/K


class Electromigration:
    def __init__(self, j: float, T: float, Ea: float = 0.9, n: float = 2.0):
        self.j = j  # current density A/cm2
        self.T = T + 273.15  # K
        self.Ea = Ea
        self.n = n

    def mttf(self, A: float = 1e-3) -> float:
        # Black's equation: MTTF = A * j^-n * exp(Ea/(kT))
        k = 8.617e-5
        return A * (self.j ** -self.n) * math.exp(self.Ea / (k * self.T))

    def is_safe(self, limit_hours: float = 1e5) -> bool:
        return self.mttf() >= limit_hours

    def max_current_density(self, target_mttf: float = 1e5) -> float:
        k = 8.617e-5
        # solve for j
        import math
        return ((1e-3 * math.exp(self.Ea / (k * self.T))) / target_mttf) ** (1.0 / self.n)


class TDDB:
    """Time-Dependent Dielectric Breakdown."""
    def __init__(self, Eox: float, T: float):
        self.Eox = Eox  # oxide field MV/cm
        self.T = T + 273.15

    def mttf(self, gamma: float = 1.0, beta: float = 0.0) -> float:
        # E-model: t_bd = tau0 * exp(-gamma * Eox) * exp(Ea/(kT))
        k = 8.617e-5
        Ea = 0.6
        tau0 = 1e-8
        return tau0 * math.exp(-gamma * self.Eox) * math.exp(Ea / (k * self.T))

    def weibull_cdf(self, t: float, beta: float = 2.0, eta: float = 1e3) -> float:
        return 1 - math.exp(-(t / eta) ** beta)

    def voltage_acceleration(self, V1: float, V2: float, gamma: float = 1.0) -> float:
        return math.exp(gamma * (V1 - V2))


class HCI:
    """Hot Carrier Injection."""
    def __init__(self, Vds: float, T: float):
        self.Vds = Vds
        self.T = T + 273.15

    def degradation_rate(self, n: float = 3.0) -> float:
        # substrate current model
        return 1e-3 * math.exp(-n * 1.0 / self.Vds) * math.exp(-0.1 / (8.617e-5 * self.T))

    def lifetime(self) -> float:
        rate = self.degradation_rate()
        if rate <= 0:
            return float("inf")
        return 0.1 / rate  # time to 10% degradation


class NBTI:
    """Negative Bias Temperature Instability."""
    def __init__(self, Vgs: float, T: float):
        self.Vgs = Vgs
        self.T = T + 273.15

    def threshold_shift(self, t: float) -> float:
        # Delta Vth = A * (t)^n * exp(-Ea/(kT)) * Vgs^m
        k = 8.617e-5
        Ea = 0.5
        n = 0.25
        A = 1e-3
        m = 2.0
        return A * (t ** n) * math.exp(-Ea / (k * self.T)) * (abs(self.Vgs) ** m)

    def recovery(self, t: float, recovery_time: float) -> float:
        # partial recovery
        return self.threshold_shift(t) * math.exp(-recovery_time / 1e3)


class ReliabilityAnalyzer:
    def __init__(self, T: float = 85.0, V: float = 1.0):
        self.T = T
        self.V = V
        self.failures: list[dict[str, Any]] = []

    def compute_fit(self, mttf_hours: float) -> float:
        # FIT = 1e9 / MTTF (in hours) ... actually 1e9 / (MTTF in hours * 1e9? )
        if mttf_hours <= 0:
            return float("inf")
        return 1e9 / (mttf_hours * 3600)  # per billion hours? simplified

    def series_reliability(self, reliabilities: list[float]) -> float:
        r = 1.0
        for ri in reliabilities:
            r *= ri
        return r

    def parallel_reliability(self, reliabilities: list[float]) -> float:
        f = 1.0
        for ri in reliabilities:
            f *= (1 - ri)
        return 1 - f

    def k_of_n_reliability(self, reliabilities: list[float], k: int) -> float:
        # probability at least k of n work
        from itertools import combinations
        n = len(reliabilities)
        total = 0.0
        for combo in combinations(range(n), k):
            p = 1.0
            for i in range(n):
                if i in combo:
                    p *= reliabilities[i]
                else:
                    p *= (1 - reliabilities[i])
            total += p
        # also k+1..n
        for kk in range(k+1, n+1):
            for combo in combinations(range(n), kk):
                p = 1.0
                for i in range(n):
                    if i in combo:
                        p *= reliabilities[i]
                    else:
                        p *= (1 - reliabilities[i])
                total += p
        return total

    def report(self) -> str:
        lines = ["Reliability Analysis Report"]
        lines.append(f"  Temperature: {self.T} C")
        lines.append(f"  Voltage: {self.V} V")
        lines.append(f"  Failures tracked: {len(self.failures)}")
        return "\n".join(lines)
