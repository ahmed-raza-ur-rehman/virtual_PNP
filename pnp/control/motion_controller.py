"""Production-grade motion controller with PID, trajectory, safety."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class PIDController:
    kp: float = 1.0
    ki: float = 0.1
    kd: float = 0.05
    integral: float = 0.0
    prev_error: float = 0.0
    integral_limit: float = 100.0
    output_limit: float = 1000.0

    def update(self, setpoint: float, measured: float, dt: float) -> float:
        error = setpoint - measured
        self.integral += error * dt
        self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        self.prev_error = error
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        output = max(-self.output_limit, min(self.output_limit, output))
        return output

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0


@dataclass
class TrajectoryPoint:
    t: float
    position: np.ndarray
    velocity: np.ndarray
    acceleration: np.ndarray


class TrajectoryGenerator:
    def __init__(self, v_max: float, a_max: float, j_max: float):
        self.v_max = v_max
        self.a_max = a_max
        self.j_max = j_max

    def plan(self, start: np.ndarray, end: np.ndarray, dt: float = 0.001) -> list:
        distance = float(np.linalg.norm(end - start))
        if distance < 1e-9:
            return [TrajectoryPoint(0.0, start.copy(), np.zeros_like(start), np.zeros_like(start))]
        direction = (end - start) / distance
        t_j = min(self.a_max / self.j_max, 1.0)
        a_peak = self.j_max * t_j
        if a_peak > self.a_max:
            a_peak = self.a_max
            t_j = self.a_max / self.j_max
        t_acc = self.v_max / a_peak + t_j if a_peak > 0 else 0.0
        d_acc = 0.5 * self.v_max * t_acc
        if 2 * d_acc > distance:
            t_acc = np.sqrt(distance / max(a_peak, 1e-9))
            d_acc = 0.5 * a_peak * t_acc * t_acc
            t_const = 0.0
        else:
            t_const = (distance - 2 * d_acc) / max(self.v_max, 1e-9)
        t_total = 2 * t_acc + t_const
        n = max(2, int(np.ceil(t_total / dt)))
        pts = []
        for i in range(n):
            t = i * dt
            if t < t_j:
                s = self.j_max * t**3 / 6.0
                v = self.j_max * t * t / 2.0
                a = self.j_max * t
            elif t < t_acc - t_j:
                s = self.j_max * t_j**3 / 6.0 + a_peak * (t - t_j)**2 / 2.0
                v = self.j_max * t_j**2 / 2.0 + a_peak * (t - t_j)
                a = a_peak
            elif t < t_acc:
                tau = t_acc - t
                s = d_acc - self.j_max * tau**3 / 6.0
                v = self.v_max - self.j_max * tau * tau / 2.0
                a = self.j_max * tau
            elif t < t_acc + t_const:
                s = d_acc + self.v_max * (t - t_acc)
                v = self.v_max
                a = 0.0
            else:
                _td = t - (t_acc + t_const)
                tau = t_total - t
                s = distance - self.j_max * tau**3 / 6.0
                v = self.j_max * tau * tau / 2.0
                a = self.j_max * tau
            s = min(distance, max(0.0, s))
            pos = start + direction * s
            vel = direction * v
            acc = direction * a
            pts.append(TrajectoryPoint(t, pos, vel, acc))
        return pts


class MotionController:
    def __init__(self, v_max=200.0, a_max=100.0, j_max=500.0):
        self.v_max = v_max
        self.a_max = a_max
        self.j_max = j_max
        self.pid_x = PIDController()
        self.pid_y = PIDController()
        self.pid_z = PIDController()
        self.trajectory = []
        self.traj_index = 0
        self.current_pos = np.zeros(3)
        self.current_vel = np.zeros(3)
        self.target_pos = np.zeros(3)
        self.enabled = False
        self.estop = False

    def enable(self):
        self.enabled = True
        self.estop = False

    def disable(self):
        self.enabled = False

    def emergency_stop(self):
        self.estop = True
        self.enabled = False
        self.current_vel = np.zeros(3)

    def set_target(self, target):
        self.target_pos = np.asarray(target, dtype=float)
        gen = TrajectoryGenerator(self.v_max, self.a_max, self.j_max)
        self.trajectory = gen.plan(self.current_pos, self.target_pos, 0.001)
        self.traj_index = 0

    def update(self, dt: float):
        if not self.enabled or self.estop:
            return self.current_pos.copy()
        if self.traj_index < len(self.trajectory):
            tp = self.trajectory[self.traj_index]
            vx = self.pid_x.update(tp.position[0], self.current_pos[0], dt)
            vy = self.pid_y.update(tp.position[1], self.current_pos[1], dt)
            vz = self.pid_z.update(tp.position[2], self.current_pos[2], dt)
            self.current_pos += np.array([vx, vy, vz]) * dt
            self.current_vel = np.array([vx, vy, vz])
            self.traj_index += 1
        return self.current_pos.copy()

    def is_complete(self):
        return self.traj_index >= len(self.trajectory)

    def get_status(self):
        return {
            "position": self.current_pos.tolist(),
            "velocity": self.current_vel.tolist(),
            "target": self.target_pos.tolist(),
            "enabled": self.enabled,
            "estop": self.estop,
            "traj_progress": self.traj_index / max(len(self.trajectory), 1),
        }
