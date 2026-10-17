"""Collision detection and avoidance."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class AABB:
    min_pt: np.ndarray
    max_pt: np.ndarray

    def intersects(self, other: AABB) -> bool:
        return (self.min_pt[0] <= other.max_pt[0] and self.max_pt[0] >= other.min_pt[0] and
                self.min_pt[1] <= other.max_pt[1] and self.max_pt[1] >= other.min_pt[1] and
                self.min_pt[2] <= other.max_pt[2] and self.max_pt[2] >= other.min_pt[2])

    def contains(self, pt: np.ndarray) -> bool:
        return np.all(pt >= self.min_pt) and np.all(pt <= self.max_pt)


@dataclass
class Sphere:
    center: np.ndarray
    radius: float

    def intersects(self, other: Sphere) -> bool:
        return np.linalg.norm(self.center - other.center) <= self.radius + other.radius

    def contains(self, pt: np.ndarray) -> bool:
        return np.linalg.norm(pt - self.center) <= self.radius


@dataclass
class OBB:
    center: np.ndarray
    half_extents: np.ndarray
    rotation: np.ndarray  # 3x3

    def intersects(self, other: OBB) -> bool:
        # SAT (simplified)
        return True  # placeholder


class CollisionChecker:
    def __init__(self):
        self.obstacles: list[Any] = []

    def add_obstacle(self, obs: Any):
        self.obstacles.append(obs)

    def remove_obstacle(self, obs: Any):
        if obs in self.obstacles:
            self.obstacles.remove(obs)

    def check_point(self, pt: np.ndarray) -> bool:
        pt = np.asarray(pt, dtype=float)
        for obs in self.obstacles:
            if isinstance(obs, Sphere) and obs.contains(pt):
                return True
            if isinstance(obs, AABB) and obs.contains(pt):
                return True
        return False

    def check_segment(self, a: np.ndarray, b: np.ndarray, num_samples: int = 20) -> bool:
        a = np.asarray(a, dtype=float)
        b = np.asarray(b, dtype=float)
        for i in range(num_samples + 1):
            pt = a + (b - a) * (i / num_samples)
            if self.check_point(pt):
                return True
        return False

    def check_aabb(self, a: AABB, b: AABB) -> bool:
        return a.intersects(b)

    def check_sphere(self, a: Sphere, b: Sphere) -> bool:
        return a.intersects(b)

    def distance_to_obstacle(self, pt: np.ndarray) -> float:
        pt = np.asarray(pt, dtype=float)
        min_dist = float("inf")
        for obs in self.obstacles:
            if isinstance(obs, Sphere):
                d = np.linalg.norm(pt - obs.center) - obs.radius
                min_dist = min(min_dist, d)
            elif isinstance(obs, AABB):
                # distance to box
                clamped = np.clip(pt, obs.min_pt, obs.max_pt)
                d = np.linalg.norm(pt - clamped)
                min_dist = min(min_dist, d)
        return min_dist

    def get_clearance(self, path: list[np.ndarray]) -> float:
        clearances = [self.distance_to_obstacle(pt) for pt in path]
        return min(clearances) if clearances else float("inf")

    def inflate_obstacles(self, margin: float):
        new_obs = []
        for obs in self.obstacles:
            if isinstance(obs, Sphere):
                new_obs.append(Sphere(center=obs.center.copy(), radius=obs.radius + margin))
            elif isinstance(obs, AABB):
                new_obs.append(AABB(min_pt=obs.min_pt - margin, max_pt=obs.max_pt + margin))
            else:
                new_obs.append(obs)
        self.obstacles = new_obs


class SweptVolume:
    def __init__(self, shape: Any, path: list[np.ndarray]):
        self.shape = shape
        self.path = path

    def compute(self) -> list[AABB]:
        boxes = []
        for pt in self.path:
            if isinstance(self.shape, Sphere):
                boxes.append(AABB(min_pt=pt - self.shape.radius, max_pt=pt + self.shape.radius))
        return boxes


class CollisionAvoidance:
    def __init__(self, checker: CollisionChecker):
        self.checker = checker

    def find_safe_point(self, pt: np.ndarray, search_radius: float = 1.0, num_samples: int = 20) -> np.ndarray | None:
        pt = np.asarray(pt, dtype=float)
        if not self.checker.check_point(pt):
            return pt
        for _ in range(num_samples):
            cand = pt + np.random.uniform(-search_radius, search_radius, pt.shape)
            if not self.checker.check_point(cand):
                return cand
        return None

    def adjust_path(self, path: list[np.ndarray], margin: float = 0.1) -> list[np.ndarray]:
        new_path = []
        for pt in path:
            if self.checker.check_point(pt):
                safe = self.find_safe_point(pt, margin)
                if safe is not None:
                    new_path.append(safe)
                else:
                    new_path.append(pt)
            else:
                new_path.append(pt)
        return new_path
