"""Physics engine for machine simulation."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class RigidBody:
    name: str
    mass: float
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    acceleration: np.ndarray = field(default_factory=lambda: np.zeros(3))
    orientation: np.ndarray = field(default_factory=lambda: np.array([0, 0, 0]))
    angular_velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    inertia: np.ndarray = field(default_factory=lambda: np.eye(3))
    forces: list[np.ndarray] = field(default_factory=list)
    torques: list[np.ndarray] = field(default_factory=list)


class PhysicsEngine:
    def __init__(self, gravity: np.ndarray | None = None):
        if gravity is None:
            gravity = np.array([0, 0, -9.81])
        self.gravity = gravity
        self.bodies: dict[str, RigidBody] = {}
        self.constraints: list[Any] = []
        self.collisions: list[tuple[str, str]] = []
        self.time = 0.0

    def add_body(self, body: RigidBody):
        self.bodies[body.name] = body

    def remove_body(self, name: str):
        self.bodies.pop(name, None)

    def apply_force(self, name: str, force: np.ndarray):
        if name in self.bodies:
            self.bodies[name].forces.append(force)

    def apply_torque(self, name: str, torque: np.ndarray):
        if name in self.bodies:
            self.bodies[name].torques.append(torque)

    def step(self, dt: float):
        for body in self.bodies.values():
            # sum forces
            F = np.sum(body.forces, axis=0) if body.forces else np.zeros(3)
            F = F + body.mass * self.gravity
            body.acceleration = F / body.mass
            body.velocity += body.acceleration * dt
            body.position += body.velocity * dt
            # angular
            tau = np.sum(body.torques, axis=0) if body.torques else np.zeros(3)
            alpha = np.linalg.solve(body.inertia, tau)
            body.angular_velocity += alpha * dt
            body.orientation += body.angular_velocity * dt
            # clear forces
            body.forces.clear()
            body.torques.clear()
        self.time += dt
        self._check_collisions()

    def _check_collisions(self):
        names = list(self.bodies.keys())
        self.collisions.clear()
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                b1 = self.bodies[names[i]]
                b2 = self.bodies[names[j]]
                dist = np.linalg.norm(b1.position - b2.position)
                if dist < 0.1:  # collision threshold
                    self.collisions.append((names[i], names[j]))

    def get_state(self) -> dict[str, Any]:
        return {
            "time": self.time,
            "bodies": {n: {"pos": b.position.tolist(), "vel": b.velocity.tolist(),
                           "acc": b.acceleration.tolist()} for n, b in self.bodies.items()},
            "collisions": self.collisions,
        }


class VacuumGripperPhysics:
    def __init__(self, max_force: float = 10.0, vacuum_pressure: float = -80000):
        self.max_force = max_force
        self.vacuum_pressure = vacuum_pressure
        self.holding = False
        self.held_object = None
        self.lift_force = 0.0

    def compute_hold_force(self, area: float) -> float:
        return abs(self.vacuum_pressure) * area

    def can_hold(self, object_mass: float, area: float) -> bool:
        hold = self.compute_hold_force(area)
        weight = object_mass * 9.81
        return hold >= weight * 1.5  # safety factor

    def pickup(self, obj_mass: float, area: float) -> bool:
        if self.can_hold(obj_mass, area):
            self.holding = True
            self.lift_force = self.compute_hold_force(area)
            return True
        return False

    def release(self):
        self.holding = False
        self.held_object = None
        self.lift_force = 0.0

    def check_slip(self, acceleration: float, friction: float = 0.5) -> bool:
        if not self.holding:
            return False
        # slip if inertial force exceeds friction
        return acceleration * 1.0 > friction * self.lift_force


class ServoMotorPhysics:
    def __init__(self, inertia: float = 1e-4, damping: float = 1e-3, torque_constant: float = 0.1, resistance: float = 1.0):
        self.inertia = inertia
        self.damping = damping
        self.kt = torque_constant
        self.R = resistance
        self.position = 0.0
        self.velocity = 0.0
        self.current = 0.0
        self.voltage = 0.0

    def update(self, voltage: float, load_torque: float, dt: float):
        self.voltage = voltage
        self.current = (voltage - self.kt * self.velocity) / self.R
        torque = self.kt * self.current - load_torque
        alpha = (torque - self.damping * self.velocity) / self.inertia
        self.velocity += alpha * dt
        self.position += self.velocity * dt

    def get_state(self) -> dict[str, float]:
        return {"position": self.position, "velocity": self.velocity, "current": self.current}


class ConveyorPhysics:
    def __init__(self, length: float, speed: float = 0.1):
        self.length = length
        self.speed = speed
        self.items: list[dict[str, Any]] = []

    def add_item(self, item: dict[str, Any]):
        item["position"] = 0.0
        self.items.append(item)

    def update(self, dt: float):
        for item in self.items:
            item["position"] += self.speed * dt
        self.items = [i for i in self.items if i["position"] < self.length]

    def get_items_at_end(self) -> list[dict[str, Any]]:
        return [i for i in self.items if i["position"] >= self.length - 0.01]


class FeederPhysics:
    def __init__(self, vibration_freq: float = 50.0, vibration_amp: float = 0.5):
        self.vibration_freq = vibration_freq
        self.vibration_amp = vibration_amp
        self.components: list[dict[str, Any]] = []
        self.time = 0.0

    def update(self, dt: float):
        self.time += dt
        vib = self.vibration_amp * math.sin(2 * math.pi * self.vibration_freq * self.time)
        for comp in self.components:
            comp["position"] += vib * dt * 0.1
            if comp["position"] > 1.0:
                comp["position"] = 1.0
                comp["ready"] = True

    def add_component(self, comp: dict[str, Any]):
        comp["position"] = 0.0
        comp["ready"] = False
        self.components.append(comp)

    def get_ready(self) -> list[dict[str, Any]]:
        return [c for c in self.components if c.get("ready")]
