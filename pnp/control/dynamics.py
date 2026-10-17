"""Robot dynamics: equations of motion, force control."""
from __future__ import annotations

import math

import numpy as np


class RobotDynamics:
    def __init__(self, masses: list[float], lengths: list[float]):
        self.masses = masses
        self.lengths = lengths
        self.n = len(masses)
        self.g = 9.81

    def mass_matrix(self, q: np.ndarray) -> np.ndarray:
        # 2-link planar arm
        if self.n == 2:
            m1, m2 = self.masses
            l1, l2 = self.lengths
            c2 = math.cos(q[1])
            M11 = m1*l1*l1/3 + m2*(l1*l1 + l2*l2/3 + l1*l2*c2) + 0  # simplified
            M12 = m2*(l2*l2/3 + 0.5*l1*l2*c2)
            M22 = m2*l2*l2/3
            return np.array([[M11, M12], [M12, M22]])
        # generic diagonal
        M = np.diag([m * l * l / 3 for m, l in zip(self.masses, self.lengths)])
        return M

    def coriolis(self, q: np.ndarray, dq: np.ndarray) -> np.ndarray:
        if self.n == 2:
            m2 = self.masses[1]
            l1, l2 = self.lengths
            math.cos(q[1])
            s2 = math.sin(q[1])
            C = np.array([
                [-m2 * l1 * l2 * s2 * dq[1], -m2 * l1 * l2 * s2 * (dq[0] + dq[1])],
                [m2 * l1 * l2 * s2 * dq[0], 0],
            ])
            return C @ dq
        return np.zeros(self.n)

    def gravity(self, q: np.ndarray) -> np.ndarray:
        if self.n == 2:
            m1, m2 = self.masses
            l1, l2 = self.lengths
            g1 = (m1 * l1 / 2 + m2 * l1) * self.g * math.cos(q[0]) + m2 * (l2 / 2) * self.g * math.cos(q[0] + q[1])
            g2 = m2 * (l2 / 2) * self.g * math.cos(q[0] + q[1])
            return np.array([g1, g2])
        return np.array([m * self.g * l / 2 * math.cos(q[i]) for i, (m, l) in enumerate(zip(self.masses, self.lengths))])

    def forward_dynamics(self, q: np.ndarray, dq: np.ndarray, tau: np.ndarray) -> np.ndarray:
        M = self.mass_matrix(q)
        C = self.coriolis(q, dq)
        G = self.gravity(q)
        ddq = np.linalg.solve(M, tau - C - G)
        return ddq

    def inverse_dynamics(self, q: np.ndarray, dq: np.ndarray, ddq: np.ndarray) -> np.ndarray:
        M = self.mass_matrix(q)
        C = self.coriolis(q, dq)
        G = self.gravity(q)
        return M @ ddq + C + G

    def compute_torque(self, q, dq, ddq):
        return self.inverse_dynamics(q, dq, ddq)


class ForceController:
    def __init__(self, kp: float = 1.0, ki: float = 0.0, kd: float = 0.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0

    def update(self, force_setpoint: float, force_measured: float, dt: float = 0.01) -> float:
        error = force_setpoint - force_measured
        self.integral += error * dt
        derivative = (error - self.prev_error) / max(dt, 1e-9)
        self.prev_error = error
        return self.kp * error + self.ki * self.integral + self.kd * derivative


class ImpedanceController:
    def __init__(self, M: np.ndarray, B: np.ndarray, K: np.ndarray):
        self.M = M
        self.B = B
        self.K = K
        self.x_d = None
        self.dx_d = None
        self.ddx_d = None

    def set_desired(self, x_d, dx_d=None, ddx_d=None):
        self.x_d = np.asarray(x_d, dtype=float)
        self.dx_d = np.asarray(dx_d, dtype=float) if dx_d is not None else np.zeros_like(self.x_d)
        self.ddx_d = np.asarray(ddx_d, dtype=float) if ddx_d is not None else np.zeros_like(self.x_d)

    def compute_force(self, x: np.ndarray, dx: np.ndarray) -> np.ndarray:
        if self.x_d is None:
            return np.zeros_like(x)
        e = self.x_d - x
        de = self.dx_d - dx
        return self.M @ self.ddx_d + self.B @ de + self.K @ e


class AdmittanceController:
    def __init__(self, M: np.ndarray, B: np.ndarray, K: np.ndarray):
        self.M = M
        self.B = B
        self.K = K

    def compute_acceleration(self, force_ext: np.ndarray, x: np.ndarray, dx: np.ndarray) -> np.ndarray:
        return np.linalg.solve(self.M, force_ext - self.B @ dx - self.K @ x)
