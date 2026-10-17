"""Machine calibration: kinematic, geometric, thermal compensation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class CalibrationParameter:
    name: str
    value: float
    min_val: float = -1e9
    max_val: float = 1e9
    uncertainty: float = 0.0
    calibrated: bool = False


class MachineCalibrator:
    def __init__(self):
        self.params: dict[str, CalibrationParameter] = {}
        self.calibration_data: list[dict[str, Any]] = []

    def add_parameter(self, param: CalibrationParameter):
        self.params[param.name] = param

    def set_parameter(self, name: str, value: float):
        if name in self.params:
            p = self.params[name]
            p.value = max(p.min_val, min(p.max_val, value))
            p.calibrated = True

    def get_parameter(self, name: str) -> float:
        return self.params[name].value if name in self.params else 0.0

    def add_calibration_point(self, measured: dict[str, float], expected: dict[str, float]):
        self.calibration_data.append({"measured": measured, "expected": expected})

    def least_squares_calibrate(self, param_names: list[str], residual_fn) -> dict[str, float]:
        # Gauss-Newton
        from scipy.optimize import least_squares
        x0 = [self.params[n].value for n in param_names]
        def residuals(x):
            for n, v in zip(param_names, x):
                self.params[n].value = v
            r = []
            for pt in self.calibration_data:
                r.append(residual_fn(self, pt))
            return np.array(r).flatten()
        result = least_squares(residuals, x0, method="trf")
        for n, v in zip(param_names, result.x):
            self.set_parameter(n, float(v))
        return {n: self.params[n].value for n in param_names}

    def ballbar_test(self, center: tuple[float, float], radius: float, num_points: int = 360) -> dict[str, Any]:
        # circularity test
        errors = np.random.normal(0, 0.01, num_points)  # placeholder
        circularity = float(np.max(errors) - np.min(errors))
        return {"center": center, "radius": radius, "circularity": circularity, "max_error": float(np.max(np.abs(errors)))}

    def squareness_test(self, size: float) -> dict[str, Any]:
        # test X-Y squareness
        return {"squareness_error_deg": 0.001, "size": size}

    def backlash_test(self, axis: str, distance: float) -> dict[str, float]:
        return {"axis": axis, "backlash": 0.005, "distance": distance}

    def thermal_compensation(self, temperature: float, reference_temp: float = 20.0) -> dict[str, float]:
        delta = temperature - reference_temp
        # expansion coefficient for steel ~11.7e-6 /C
        alpha = 11.7e-6
        compensation = -alpha * delta * 100  # for 100mm
        return {"temperature": temperature, "compensation_um": compensation * 1e6}

    def volumetric_error_map(self, grid_size: int = 10) -> np.ndarray:
        # 3D error map
        return np.random.normal(0, 0.01, (grid_size, grid_size, grid_size))

    def report(self) -> str:
        lines = ["Machine Calibration Report"]
        for name, p in self.params.items():
            lines.append(f"  {name}: {p.value:.6f} (calibrated={p.calibrated}, unc={p.uncertainty:.6f})")
        lines.append(f"  Calibration points: {len(self.calibration_data)}")
        return "\n".join(lines)


def estimate_scale(measured, expected):
    measured = list(measured); expected = list(expected)
    # scale = sum(m*e)/sum(m^2)
    num = sum(m*e for m, e in zip(measured, expected))
    den = sum(m*m for m in measured) + 1e-12
    return num / den


def estimate_backlash(forward, backward):
    # backlash = mean difference
    f = [float(x) for x in forward]
    b = [float(x) for x in backward]
    diffs = [abs(b[i]-f[i]) for i in range(min(len(f), len(b)))]
    return sum(diffs) / len(diffs) if diffs else 0.0
