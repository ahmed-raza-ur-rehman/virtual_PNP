"""Multi-axis coordination and synchronization."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class Axis:
    id: int
    name: str
    position: float = 0.0
    velocity: float = 0.0
    acceleration: float = 0.0
    target: float = 0.0
    enabled: bool = False
    homed: bool = False
    limits: tuple[float, float] = (-1e9, 1e9)


class MultiAxisController:
    def __init__(self, num_axes: int):
        self.axes: list[Axis] = [Axis(id=i, name=f"axis_{i}") for i in range(num_axes)]
        self.sync_groups: dict[str, list[int]] = {}
        self.gear_ratios: dict[int, float] = {}
        self.cam_profiles: dict[int, list[tuple[float, float]]] = {}

    def enable_axis(self, axis_id: int):
        self.axes[axis_id].enabled = True

    def disable_axis(self, axis_id: int):
        self.axes[axis_id].enabled = False

    def set_target(self, axis_id: int, target: float):
        ax = self.axes[axis_id]
        ax.target = max(ax.limits[0], min(ax.limits[1], target))

    def home_axis(self, axis_id: int):
        self.axes[axis_id].position = 0.0
        self.axes[axis_id].homed = True

    def home_all(self):
        for ax in self.axes:
            self.home_axis(ax.id)

    def update(self, dt: float):
        for ax in self.axes:
            if not ax.enabled:
                continue
            # simple P control
            error = ax.target - ax.position
            vel = error * 5.0
            vel = max(-100, min(100, vel))
            ax.velocity = vel
            ax.position += vel * dt
            ax.acceleration = (vel - ax.velocity) / max(dt, 1e-9) if False else 0.0

    def create_sync_group(self, name: str, axis_ids: list[int]):
        self.sync_groups[name] = list(axis_ids)

    def sync_move(self, group_name: str, targets: list[float]):
        axes = self.sync_groups.get(group_name, [])
        for ax_id, tgt in zip(axes, targets):
            self.set_target(ax_id, tgt)

    def set_gear_ratio(self, slave_axis: int, master_axis: int, ratio: float):
        self.gear_ratios[slave_axis] = ratio

    def apply_gearing(self):
        for slave, ratio in self.gear_ratios.items():
            # find master (simplified: master is 0)
            master_pos = self.axes[0].position
            self.axes[slave].target = master_pos * ratio

    def set_cam_profile(self, axis_id: int, profile: list[tuple[float, float]]):
        self.cam_profiles[axis_id] = profile

    def evaluate_cam(self, axis_id: int, master_pos: float) -> float:
        profile = self.cam_profiles.get(axis_id, [])
        if not profile:
            return 0.0
        # linear interpolation
        for i in range(len(profile) - 1):
            if profile[i][0] <= master_pos <= profile[i+1][0]:
                t = (master_pos - profile[i][0]) / (profile[i+1][0] - profile[i][0] + 1e-9)
                return profile[i][1] + t * (profile[i+1][1] - profile[i][1])
        return profile[-1][1]

    def check_limits(self) -> list[str]:
        violations = []
        for ax in self.axes:
            if ax.position < ax.limits[0] or ax.position > ax.limits[1]:
                violations.append(f"Axis {ax.id} limit violation: {ax.position}")
        return violations

    def get_status(self) -> dict[str, Any]:
        return {
            "axes": [{"id": a.id, "name": a.name, "pos": a.position, "vel": a.velocity,
                      "target": a.target, "enabled": a.enabled, "homed": a.homed} for a in self.axes],
            "sync_groups": list(self.sync_groups.keys()),
            "gear_ratios": self.gear_ratios,
        }


class ElectronicGearbox:
    def __init__(self, master: int, slave: int, ratio: float):
        self.master = master
        self.slave = slave
        self.ratio = ratio
        self.offset = 0.0

    def update(self, master_pos: float) -> float:
        return master_pos * self.ratio + self.offset

    def set_offset(self, offset: float):
        self.offset = offset


class CamGenerator:
    @staticmethod
    def polynomial_cam(master_range: tuple[float, float], slave_range: tuple[float, float], degree: int = 3) -> list[tuple[float, float]]:
        points = []
        n = 20
        for i in range(n + 1):
            t = i / n
            m = master_range[0] + t * (master_range[1] - master_range[0])
            s = slave_range[0] + (3*t*t - 2*t*t*t) * (slave_range[1] - slave_range[0])
            points.append((m, s))
        return points

    @staticmethod
    def sinusoidal_cam(master_range, slave_range, amplitude: float = 1.0) -> list[tuple[float, float]]:
        points = []
        n = 40
        for i in range(n + 1):
            t = i / n
            m = master_range[0] + t * (master_range[1] - master_range[0])
            s = slave_range[0] + amplitude * math.sin(2 * math.pi * t) * (slave_range[1] - slave_range[0])
            points.append((m, s))
        return points
