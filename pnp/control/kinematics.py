"""Kinematics for multi-axis pick-and-place."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class Link:
    length: float
    angle: float = 0.0
    offset: np.ndarray | None = None


class ForwardKinematics:
    def __init__(self, links: list[Link]):
        self.links = links

    def compute(self, joint_angles: np.ndarray) -> np.ndarray:
        # 2D planar
        x = 0.0; y = 0.0; theta = 0.0
        for i, link in enumerate(self.links):
            theta += joint_angles[i] if i < len(joint_angles) else 0
            x += link.length * math.cos(theta)
            y += link.length * math.sin(theta)
        return np.array([x, y, theta])

    def jacobian(self, joint_angles: np.ndarray) -> np.ndarray:
        n = len(self.links)
        J = np.zeros((3, n))
        # compute partial derivatives
        for j in range(n):
            sum(joint_angles[:j+1])
            # contribution of joint j to end effector
            rx = 0.0; ry = 0.0
            for i in range(j, n):
                ti = sum(joint_angles[:i+1])
                rx -= self.links[i].length * math.sin(ti)
                ry += self.links[i].length * math.cos(ti)
            J[0, j] = rx
            J[1, j] = ry
            J[2, j] = 1.0
        return J


class InverseKinematics:
    def __init__(self, fk: ForwardKinematics, max_iters: int = 100, tol: float = 1e-6):
        self.fk = fk
        self.max_iters = max_iters
        self.tol = tol

    def solve(self, target: np.ndarray, initial: np.ndarray | None = None) -> np.ndarray:
        if initial is None:
            initial = np.zeros(len(self.fk.links))
        q = initial.copy()
        for _ in range(self.max_iters):
            pos = self.fk.compute(q)[:2]
            err = target[:2] - pos
            if np.linalg.norm(err) < self.tol:
                break
            J = self.fk.jacobian(q)[:2, :]
            # pseudoinverse
            try:
                dq = np.linalg.lstsq(J, err, rcond=None)[0]
            except np.linalg.LinAlgError:
                break
            q += dq * 0.5
            # clamp
            q = np.clip(q, -math.pi, math.pi)
        return q

    def solve_analytical_2link(self, target: np.ndarray, l1: float, l2: float) -> list[np.ndarray]:
        x, y = target[0], target[1]
        r = math.hypot(x, y)
        if r > l1 + l2 or r < abs(l1 - l2):
            return []
        cos2 = (r*r - l1*l1 - l2*l2) / (2*l1*l2)
        cos2 = max(-1, min(1, cos2))
        sin2 = math.sqrt(1 - cos2*cos2)
        theta2_pos = math.atan2(sin2, cos2)
        theta2_neg = math.atan2(-sin2, cos2)
        solutions = []
        for theta2 in (theta2_pos, theta2_neg):
            k1 = l1 + l2 * math.cos(theta2)
            k2 = l2 * math.sin(theta2)
            theta1 = math.atan2(y, x) - math.atan2(k2, k1)
            solutions.append(np.array([theta1, theta2]))
        return solutions


class DeltaKinematics:
    """Delta robot (3-DOF parallel)."""
    def __init__(self, R: float = 100.0, r: float = 30.0, L: float = 200.0, l: float = 50.0):
        self.R = R
        self.r = r
        self.L = L
        self.l = l

    def forward(self, theta1: float, theta2: float, theta3: float) -> np.ndarray:
        # simplified
        th = [theta1, theta2, theta3]
        x = sum(self.L * math.cos(t) for t in th) / 3
        y = sum(self.L * math.sin(t) for t in th) / 3
        z = -self.l
        return np.array([x, y, z])

    def inverse(self, x: float, y: float, z: float) -> list[float] | None:
        # simplified: return approximate angles
        angles = []
        for i in range(3):
            angle = math.atan2(y, x) + 2 * math.pi * i / 3
            angles.append(angle)
        return angles


class SCARAKinematics:
    def __init__(self, l1: float, l2: float, d3_range: tuple[float, float]):
        self.l1 = l1
        self.l2 = l2
        self.d3_range = d3_range

    def forward(self, theta1: float, theta2: float, d3: float, theta4: float) -> np.ndarray:
        x = self.l1 * math.cos(theta1) + self.l2 * math.cos(theta1 + theta2)
        y = self.l1 * math.sin(theta1) + self.l2 * math.sin(theta1 + theta2)
        z = d3
        return np.array([x, y, z, theta1 + theta2 + theta4])

    def inverse(self, x: float, y: float, z: float, phi: float) -> list[float] | None:
        r = math.hypot(x, y)
        if r > self.l1 + self.l2 or r < abs(self.l1 - self.l2):
            return None
        cos2 = (r*r - self.l1*self.l1 - self.l2*self.l2) / (2*self.l1*self.l2)
        cos2 = max(-1, min(1, cos2))
        theta2 = math.acos(cos2)
        theta1 = math.atan2(y, x) - math.atan2(self.l2 * math.sin(theta2), self.l1 + self.l2 * math.cos(theta2))
        theta4 = phi - theta1 - theta2
        return [theta1, theta2, z, theta4]


class CoordinateTransform:
    @staticmethod
    def rotation_matrix_2d(theta: float) -> np.ndarray:
        c, s = math.cos(theta), math.sin(theta)
        return np.array([[c, -s], [s, c]])

    @staticmethod
    def rotation_matrix_3d_xyz(rx: float, ry: float, rz: float) -> np.ndarray:
        cx, sx = math.cos(rx), math.sin(rx)
        cy, sy = math.cos(ry), math.sin(ry)
        cz, sz = math.cos(rz), math.sin(rz)
        Rx = np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
        Ry = np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
        Rz = np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])
        return Rz @ Ry @ Rx

    @staticmethod
    def homogeneous_transform(R: np.ndarray, t: np.ndarray) -> np.ndarray:
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = t
        return T

    @staticmethod
    def transform_point(T: np.ndarray, p: np.ndarray) -> np.ndarray:
        p_h = np.append(p, 1.0)
        return (T @ p_h)[:3]

    @staticmethod
    def inverse_transform(T: np.ndarray) -> np.ndarray:
        R = T[:3, :3]
        t = T[:3, 3]
        Tinv = np.eye(4)
        Tinv[:3, :3] = R.T
        Tinv[:3, 3] = -R.T @ t
        return Tinv
