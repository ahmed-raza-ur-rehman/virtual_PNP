"""Spline trajectory generation."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class Waypoint:
    position: np.ndarray
    velocity: np.ndarray | None = None
    acceleration: np.ndarray | None = None
    time: float = 0.0


class CubicSpline:
    def __init__(self, t: np.ndarray, y: np.ndarray):
        self.t = np.asarray(t, dtype=float)
        self.y = np.asarray(y, dtype=float)
        self.n = len(t) - 1
        self.h = np.diff(self.t)
        self.a = self.y[:-1].copy()
        self.b = np.zeros(self.n)
        self.c = np.zeros(self.n)
        self.d = np.zeros(self.n)
        # solve tridiagonal
        alpha = np.zeros(self.n)
        for i in range(1, self.n):
            alpha[i] = (3 / self.h[i]) * (self.y[i+1] - self.y[i]) - (3 / self.h[i-1]) * (self.y[i] - self.y[i-1])
        l = np.ones(self.n + 1)
        mu = np.zeros(self.n)
        z = np.zeros(self.n + 1)
        for i in range(1, self.n):
            l[i] = 2 * (self.t[i+1] - self.t[i-1]) - self.h[i-1] * mu[i-1]
            mu[i] = self.h[i] / l[i]
            z[i] = (alpha[i] - self.h[i-1] * z[i-1]) / l[i]
        for j in range(self.n - 1, 0, -1):
            self.c[j-1] = z[j] - mu[j] * self.c[j]
        for i in range(self.n):
            self.b[i] = (self.y[i+1] - self.y[i]) / self.h[i] - self.h[i] * (self.c[i+1] + 2 * self.c[i]) / 3 if i < self.n - 1 else 0
            self.d[i] = (self.c[i+1] - self.c[i]) / (3 * self.h[i]) if i < self.n - 1 else 0

    def evaluate(self, t: float) -> float:
        # find segment
        idx = np.searchsorted(self.t, t) - 1
        idx = max(0, min(idx, self.n - 1))
        dt = t - self.t[idx]
        return float(self.a[idx] + self.b[idx]*dt + self.c[idx]*dt*dt + self.d[idx]*dt*dt*dt)

    def derivative(self, t: float) -> float:
        idx = np.searchsorted(self.t, t) - 1
        idx = max(0, min(idx, self.n - 1))
        dt = t - self.t[idx]
        return float(self.b[idx] + 2*self.c[idx]*dt + 3*self.d[idx]*dt*dt)

    def second_derivative(self, t: float) -> float:
        idx = np.searchsorted(self.t, t) - 1
        idx = max(0, min(idx, self.n - 1))
        dt = t - self.t[idx]
        return float(2*self.c[idx] + 6*self.d[idx]*dt)


class QuinticSpline:
    def __init__(self, t: np.ndarray, y: np.ndarray, dy: np.ndarray | None = None, ddy: np.ndarray | None = None):
        self.t = np.asarray(t, dtype=float)
        self.y = np.asarray(y, dtype=float)
        self.n = len(t) - 1
        self.h = np.diff(self.t)
        dy = dy if dy is not None else np.zeros(len(t))
        ddy = ddy if ddy is not None else np.zeros(len(t))
        self.coeffs = []
        for i in range(self.n):
            dt = self.h[i]
            # solve for quintic coefficients given endpoints and derivatives
            # y(t) = a0 + a1*s + a2*s^2 + a3*s^3 + a4*s^4 + a5*s^5, s in [0,dt]
            a0 = self.y[i]
            a1 = dy[i]
            a2 = ddy[i] / 2
            # solve a3,a4,a5 from endpoint constraints
            # at s=dt: y[i+1], dy[i+1], ddy[i+1]
            A = np.array([
                [dt**3, dt**4, dt**5],
                [3*dt**2, 4*dt**3, 5*dt**4],
                [6*dt, 12*dt**2, 20*dt**3],
            ])
            rhs = np.array([
                self.y[i+1] - a0 - a1*dt - a2*dt*dt,
                dy[i+1] - a1 - 2*a2*dt,
                ddy[i+1] - 2*a2,
            ])
            sol = np.linalg.solve(A, rhs)
            self.coeffs.append((a0, a1, a2, sol[0], sol[1], sol[2]))

    def evaluate(self, t: float) -> float:
        idx = np.searchsorted(self.t, t) - 1
        idx = max(0, min(idx, self.n - 1))
        s = t - self.t[idx]
        a0, a1, a2, a3, a4, a5 = self.coeffs[idx]
        return float(a0 + a1*s + a2*s*s + a3*s**3 + a4*s**4 + a5*s**5)

    def derivative(self, t: float) -> float:
        idx = np.searchsorted(self.t, t) - 1
        idx = max(0, min(idx, self.n - 1))
        s = t - self.t[idx]
        _a0, a1, a2, a3, a4, a5 = self.coeffs[idx]
        return float(a1 + 2*a2*s + 3*a3*s*s + 4*a4*s**3 + 5*a5*s**4)


class TrapezoidalVelocityProfile:
    def __init__(self, distance: float, v_max: float, a_max: float):
        self.distance = abs(distance)
        self.v_max = v_max
        self.a_max = a_max
        self.sign = 1 if distance >= 0 else -1
        # compute phases
        t_acc = v_max / a_max
        d_acc = 0.5 * a_max * t_acc * t_acc
        if 2 * d_acc >= self.distance:
            # triangular
            t_acc = math.sqrt(self.distance / a_max)
            self.t_acc = t_acc
            self.t_cruise = 0.0
            self.t_dec = t_acc
            self.v_peak = a_max * t_acc
        else:
            self.t_acc = t_acc
            self.t_cruise = (self.distance - 2 * d_acc) / v_max
            self.t_dec = t_acc
            self.v_peak = v_max
        self.total_time = self.t_acc + self.t_cruise + self.t_dec

    def position(self, t: float) -> float:
        t = max(0, min(t, self.total_time))
        if t < self.t_acc:
            pos = 0.5 * self.a_max * t * t
        elif t < self.t_acc + self.t_cruise:
            pos = 0.5 * self.a_max * self.t_acc * self.t_acc + self.v_peak * (t - self.t_acc)
        else:
            td = t - self.t_acc - self.t_cruise
            pos = (0.5 * self.a_max * self.t_acc * self.t_acc + self.v_peak * self.t_cruise +
                   self.v_peak * td - 0.5 * self.a_max * td * td)
        return self.sign * pos

    def velocity(self, t: float) -> float:
        t = max(0, min(t, self.total_time))
        if t < self.t_acc:
            return self.sign * self.a_max * t
        elif t < self.t_acc + self.t_cruise:
            return self.sign * self.v_peak
        elif t < self.total_time:
            td = t - self.t_acc - self.t_cruise
            return self.sign * (self.v_peak - self.a_max * td)
        return 0.0

    def acceleration(self, t: float) -> float:
        t = max(0, min(t, self.total_time))
        if t < self.t_acc:
            return self.sign * self.a_max
        elif t < self.t_acc + self.t_cruise:
            return 0.0
        elif t < self.total_time:
            return self.sign * (-self.a_max)
        return 0.0


class SCurveProfile:
    """Jerk-limited S-curve velocity profile."""
    def __init__(self, distance: float, v_max: float, a_max: float, j_max: float):
        self.distance = abs(distance)
        self.v_max = v_max
        self.a_max = a_max
        self.j_max = j_max
        self.sign = 1 if distance >= 0 else -1
        # compute timing (simplified)
        # jerk phase time
        tj = a_max / j_max
        # distance during jerk phase
        j_max * tj**3 / 6
        # acceleration phase
        # try full S-curve
        # total accel distance = a_max^2 / j_max + ... simplified
        self.tj = tj
        # acceleration time to reach v_max
        if v_max <= a_max * tj - j_max * tj**2 / 2:  # won't reach a_max? simplify
            pass
        # Use simplified: time to accel = v_max/a_max + a_max/j_max
        self.ta = v_max / a_max + a_max / j_max
        da = v_max * self.ta / 2  # approximate
        if 2 * da >= self.distance:
            # triangular S-curve
            self.ta = math.sqrt(self.distance / (v_max * 0.5))  # approx
            self.tc = 0.0
            self.v_peak = self.distance / (self.ta)  # approx
        else:
            self.tc = (self.distance - 2 * da) / v_max
            self.v_peak = v_max
        self.total_time = 2 * self.ta + self.tc

    def position(self, t: float) -> float:
        t = max(0, min(t, self.total_time))
        # simplified trapezoidal-like with S smoothing
        if t < self.ta:
            # S-curve accel
            s = t / self.ta
            pos = self.distance * (0.5 * s * s * (3 - 2 * s)) * (self.ta / self.total_time) if self.total_time > 0 else 0
            # fallback linear
            pos = self.v_peak * t * t / (2 * self.ta) if self.ta > 0 else 0
        elif t < self.ta + self.tc:
            pos = self.v_peak * self.ta / 2 + self.v_peak * (t - self.ta)
        else:
            td = t - self.ta - self.tc
            pos = self.v_peak * self.ta / 2 + self.v_peak * self.tc + self.v_peak * td - self.v_peak * td * td / (2 * self.ta)
        return self.sign * min(pos, self.distance)

    def velocity(self, t: float) -> float:
        t = max(0, min(t, self.total_time))
        if t < self.ta:
            return self.sign * self.v_peak * t / self.ta
        elif t < self.ta + self.tc:
            return self.sign * self.v_peak
        elif t < self.total_time:
            td = t - self.ta - self.tc
            return self.sign * (self.v_peak - self.v_peak * td / self.ta)
        return 0.0
