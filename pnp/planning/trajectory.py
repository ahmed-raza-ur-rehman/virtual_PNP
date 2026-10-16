"""Trajectory planning: S-curve, trapezoidal, jerk-limited, collision-aware."""

from __future__ import annotations

import numpy as np


def s_curve_1d(distance: float, v_max: float, a_max: float, j_max: float, dt: float):
    distance = abs(distance)
    if distance < 1e-9:
        return np.array([0.0]), np.array([0.0]), np.array([0.0])
    # jerk phase duration
    t_j = min(a_max / max(j_max, 1e-9), 1.0)
    a_peak = j_max * t_j
    if a_peak > a_max:
        a_peak = a_max
        t_j = a_max / j_max
    # accel phase duration to reach v_max
    t_acc = v_max / a_peak + t_j if a_peak > 0 else 0.0
    d_acc = 0.5 * v_max * t_acc
    if 2 * d_acc > distance:
        t_acc = np.sqrt(distance / max(a_peak, 1e-9) * 0.9)
        d_acc = 0.5 * a_peak * t_acc * t_acc * 0.5
        t_const = 0.0
    else:
        t_const = (distance - 2 * d_acc) / max(v_max, 1e-9)
    t_total = 2 * t_acc + t_const
    n = max(2, int(np.ceil(t_total / dt)))
    ts = np.linspace(0, t_total, n)
    pos = np.zeros(n)
    vel = np.zeros(n)
    acc = np.zeros(n)
    for i, t in enumerate(ts):
        if t < t_j:
            acc[i] = j_max * t
            vel[i] = 0.5 * j_max * t * t
            pos[i] = j_max * t**3 / 6.0
        elif t < t_acc - t_j:
            acc[i] = a_peak
            vel[i] = 0.5 * j_max * t_j * t_j + a_peak * (t - t_j)  # approx
            pos[i] = (
                j_max * t_j**3 / 6.0
                + a_peak * (t - t_j) * (t - t_j) / 2.0
                + 0.5 * j_max * t_j * t_j * (t - t_j)
            )
        elif t < t_acc:
            tau = t_acc - t
            acc[i] = j_max * tau
            vel[i] = v_max - 0.5 * j_max * tau * tau
            pos[i] = d_acc - j_max * tau**3 / 6.0
        elif t < t_acc + t_const:
            acc[i] = 0.0
            vel[i] = v_max
            pos[i] = d_acc + v_max * (t - t_acc)
        else:
            td = t - (t_acc + t_const)
            if td < t_j:
                acc[i] = -j_max * td
                vel[i] = v_max - 0.5 * j_max * td * td
            elif td < t_acc - t_j:
                acc[i] = -a_peak
                vel[i] = v_max - (0.5 * j_max * t_j * t_j + a_peak * (td - t_j))
            else:
                tau = t_total - t
                acc[i] = j_max * tau
                vel[i] = 0.5 * j_max * tau * tau
            pos[i] = distance - (t_total - t) * v_max * 0.5
    pos = np.clip(pos, 0, distance)
    if pos[-1] > 0:
        pos = pos / pos[-1] * distance
    return pos, vel, acc


def plan_path(waypoints: np.ndarray, v_max=200.0, a_max=100.0, j_max=500.0, dt=0.01):
    wps = np.asarray(waypoints, dtype=float)
    segments = []
    for i in range(len(wps) - 1):
        d = float(np.hypot(wps[i + 1, 0] - wps[i, 0], wps[i + 1, 1] - wps[i, 1]))
        pos, vel, acc = s_curve_1d(d, v_max, a_max, j_max, dt)
        ang = np.arctan2(wps[i + 1, 1] - wps[i, 1], wps[i + 1, 0] - wps[i, 0])
        xs = wps[i, 0] + pos * np.cos(ang)
        ys = wps[i, 1] + pos * np.sin(ang)
        segments.append({"t": np.arange(len(pos)) * dt, "x": xs, "y": ys, "vel": vel, "acc": acc})
    return segments


def collision_free(points: np.ndarray, obstacles: list[tuple[float, float, float]]) -> bool:
    pts = np.asarray(points, dtype=float)
    for i in range(len(pts) - 1):
        for ox, oy, r in obstacles:
            a = pts[i]
            b = pts[i + 1]
            ab = b - a
            denom = float(np.dot(ab, ab)) + 1e-12
            t = float(np.dot(np.array([ox, oy]) - a, ab) / denom)
            t = float(np.clip(t, 0.0, 1.0))
            closest = a + t * ab
            if np.hypot(closest[0] - ox, closest[1] - oy) < r:
                return False
    return True
