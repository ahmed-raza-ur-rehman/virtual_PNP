"""Signal integrity analysis."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class TransmissionLine:
    length: float  # meters
    width: float
    height: float
    er: float = 4.0  # relative permittivity
    zo: float = 50.0  # characteristic impedance


class SignalIntegrityAnalyzer:
    def __init__(self):
        self.lines: list[TransmissionLine] = []

    def add_line(self, line: TransmissionLine):
        self.lines.append(line)

    def propagation_delay(self, line: TransmissionLine) -> float:
        c = 3e8
        v = c / math.sqrt(line.er)
        return line.length / v

    def reflection_coefficient(self, zo: float, zl: float) -> float:
        return (zl - zo) / (zl + zo + 1e-9)

    def vswr(self, gamma: float) -> float:
        if abs(gamma) >= 1:
            return float("inf")
        return (1 + abs(gamma)) / (1 - abs(gamma))

    def return_loss(self, gamma: float) -> float:
        if abs(gamma) == 0:
            return float("inf")
        return -20 * math.log10(abs(gamma))

    def insertion_loss(self, freq: float, length: float, alpha: float = 0.1) -> float:
        return alpha * length * freq / 1e9

    def crosstalk(self, aggressor_amp: float, coupling: float) -> float:
        return aggressor_amp * coupling

    def eye_diagram(self, signal: np.ndarray, ui: int) -> dict[str, Any]:
        # group signal into unit intervals
        eyes = []
        for i in range(0, len(signal) - ui, ui):
            eyes.append(signal[i:i+ui])
        if not eyes:
            return {"width": 0, "height": 0, "open": False}
        eyes = np.array(eyes)
        # eye opening = min - max of overlapping
        upper = eyes.max(axis=0)
        lower = eyes.min(axis=0)
        opening = (lower - upper).min() if len(eyes) > 1 else 0
        return {"width": ui, "height": float(opening), "open": opening > 0, "num_eyes": len(eyes)}

    def jitter_analysis(self, edges: np.ndarray) -> dict[str, float]:
        if len(edges) < 2:
            return {"rj": 0, "dj": 0, "tj": 0}
        periods = np.diff(edges)
        mean_p = periods.mean()
        rj = periods.std()
        # deterministic jitter: peak-to-peak - random
        dj = periods.max() - periods.min() - 3 * rj
        tj = periods.max() - periods.min()
        return {"rj": float(rj), "dj": float(dj), "tj": float(tj), "mean_period": float(mean_p)}

    def impedance_control(self, trace_width: float, trace_height: float, er: float) -> float:
        # microstrip impedance (simplified Hammerstad)
        w_h = trace_width / trace_height
        if w_h <= 1:
            zo = (87 / math.sqrt(er + 1.41)) * math.log(5.98 * (trace_height + 0.8 * trace_width) / (0.8 * trace_width + trace_height))
        else:
            zo = (120 * math.pi / math.sqrt(er)) / (w_h + 1.393 + 0.667 * math.log(w_h + 1.444))
        return zo


class PowerIntegrity:
    def __init__(self):
        self.pdn: dict[str, float] = {}

    def add_capacitor(self, freq: float, value: float, esr: float, esl: float):
        # impedance of capacitor
        z = complex(esr, 2 * math.pi * freq * esl - 1 / (2 * math.pi * freq * value + 1e-12))
        self.pdn[freq] = abs(z)

    def target_impedance(self, voltage: float, ripple_percent: float, current: float) -> float:
        ripple = voltage * ripple_percent / 100.0
        return ripple / (current + 1e-9)

    def decoupling_strategy(self, target_z: float, freqs: list[float]) -> list[dict[str, Any]]:
        result = []
        for f in freqs:
            # suggest capacitor value
            c = 1.0 / (2 * math.pi * f * target_z + 1e-12)
            result.append({"freq": f, "capacitance": c, "target_z": target_z})
        return result

    def ir_drop(self, current: float, resistance: float) -> float:
        return current * resistance

    def pdn_impedance(self, freqs: list[float], caps: list[tuple[float, float, float]]) -> list[float]:
        # caps: (value, esr, esl)
        zs = []
        for f in freqs:
            y_total = 0+0j
            for c, esr, esl in caps:
                z = complex(esr, 2*math.pi*f*esl - 1/(2*math.pi*f*c+1e-12))
                y_total += 1.0 / (z + 1e-12)
            zs.append(abs(1.0 / (y_total + 1e-12)))
        return zs
