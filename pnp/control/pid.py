"""PID controller variants."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class PIDGains:
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0


class PIDController:
    def __init__(self, gains: PIDGains, output_limits: tuple[float, float] = (-float("inf"), float("inf")),
                 integral_limits: tuple[float, float] = (-float("inf"), float("inf")), sample_time: float = 0.01):
        self.gains = gains
        self.output_limits = output_limits
        self.integral_limits = integral_limits
        self.sample_time = sample_time
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_measurement = 0.0
        self.prev_output = 0.0
        self.derivative_filter = 0.0

    def update(self, setpoint: float, measurement: float, dt: float | None = None) -> float:
        dt = dt or self.sample_time
        error = setpoint - measurement
        # proportional
        P = self.gains.kp * error
        # integral with anti-windup
        self.integral += error * dt
        self.integral = max(self.integral_limits[0], min(self.integral_limits[1], self.integral))
        I = self.gains.ki * self.integral
        # derivative on measurement (avoid derivative kick)
        derivative = (measurement - self.prev_measurement) / max(dt, 1e-9)
        D = -self.gains.kd * derivative
        output = P + I + D
        output = max(self.output_limits[0], min(self.output_limits[1], output))
        self.prev_error = error
        self.prev_measurement = measurement
        self.prev_output = output
        return output

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_measurement = 0.0
        self.prev_output = 0.0

    def set_gains(self, kp=None, ki=None, kd=None):
        if kp is not None:
            self.gains.kp = kp
        if ki is not None:
            self.gains.ki = ki
        if kd is not None:
            self.gains.kd = kd

    def get_state(self) -> dict[str, float]:
        return {"integral": self.integral, "prev_error": self.prev_error, "prev_measurement": self.prev_measurement}


class CascadePID:
    def __init__(self, outer_gains: PIDGains, inner_gains: PIDGains, outer_limits=(-100, 100), inner_limits=(-100, 100)):
        self.outer = PIDController(outer_gains, outer_limits)
        self.inner = PIDController(inner_gains, inner_limits)

    def update(self, setpoint: float, outer_meas: float, inner_meas: float, dt: float = 0.01) -> float:
        outer_out = self.outer.update(setpoint, outer_meas, dt)
        return self.inner.update(outer_out, inner_meas, dt)

    def reset(self):
        self.outer.reset()
        self.inner.reset()


class FeedforwardPID:
    def __init__(self, gains: PIDGains, feedforward_gain: float = 1.0):
        self.pid = PIDController(gains)
        self.ff_gain = feedforward_gain

    def update(self, setpoint: float, measurement: float, feedforward: float = 0.0, dt: float = 0.01) -> float:
        pid_out = self.pid.update(setpoint, measurement, dt)
        return pid_out + self.ff_gain * feedforward


class AdaptivePID:
    def __init__(self, gains: PIDGains, adaptation_rate: float = 0.01):
        self.pid = PIDController(gains)
        self.adaptation_rate = adaptation_rate
        self.error_history: list[float] = []

    def update(self, setpoint: float, measurement: float, dt: float = 0.01) -> float:
        error = setpoint - measurement
        self.error_history.append(error)
        if len(self.error_history) > 100:
            self.error_history.pop(0)
        # adapt gains based on error variance
        if len(self.error_history) > 10:
            var = np.var(self.error_history[-10:]) if False else self._var(self.error_history[-10:])
            if var > 1.0:
                self.pid.gains.kp *= (1 + self.adaptation_rate)
                self.pid.gains.kd *= (1 + self.adaptation_rate)
        return self.pid.update(setpoint, measurement, dt)

    def _var(self, data):
        m = sum(data) / len(data)
        return sum((x - m) ** 2 for x in data) / len(data)


class FractionalPID:
    def __init__(self, kp: float, ki: float, kd: float, lam: float = 0.5, mu: float = 0.5):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.lam = lam
        self.mu = mu
        self.integral_history: list[float] = []
        self.error_history: list[float] = []

    def update(self, setpoint: float, measurement: float, dt: float = 0.01) -> float:
        error = setpoint - measurement
        self.error_history.append(error)
        # fractional integral (simplified)
        integral = sum(self.error_history) * dt ** self.lam
        # fractional derivative (simplified)
        if len(self.error_history) >= 2:
            derivative = (self.error_history[-1] - self.error_history[-2]) / dt ** self.mu
        else:
            derivative = 0.0
        return self.kp * error + self.ki * integral + self.kd * derivative


class AutoTuner:
    """Ziegler-Nichols auto-tuning."""
    def __init__(self):
        self.ku = 0.0
        self.tu = 0.0

    def ziegler_nichols_pid(self, ku: float, tu: float) -> PIDGains:
        return PIDGains(kp=0.6 * ku, ki=1.2 * ku / tu, kd=0.075 * ku * tu)

    def ziegler_nichols_pi(self, ku: float, tu: float) -> PIDGains:
        return PIDGains(kp=0.45 * ku, ki=0.54 * ku / tu, kd=0.0)

    def cohen_coon(self, K: float, tau: float, theta: float) -> PIDGains:
        kp = (1.0 / K) * (tau / theta) * (1.33 + 0.34 * (theta / tau)) if theta > 0 else 1.0
        ti = theta * (2.5 + (0.47 * theta / tau)) / (1 + 0.62 * (theta / tau)) if theta > 0 else 1.0
        td = (0.37 * theta) / (1 + 0.2 * (theta / tau)) if theta > 0 else 0.0
        ki = kp / ti if ti > 0 else 0.0
        kd = kp * td
        return PIDGains(kp=kp, ki=ki, kd=kd)

    def relay_feedback(self, oscillation_amplitude: float, relay_amplitude: float, period: float) -> tuple[float, float]:
        ku = 4 * relay_amplitude / (math.pi * oscillation_amplitude)
        tu = period
        return ku, tu
