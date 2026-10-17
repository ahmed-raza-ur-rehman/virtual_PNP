"""Safety monitoring and interlocks."""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class SafetyLevel(Enum):
    NORMAL = 0
    WARNING = 1
    ERROR = 2
    CRITICAL = 3
    EMERGENCY = 4


@dataclass
class SafetyZone:
    name: str
    min_pos: tuple[float, float, float]
    max_pos: tuple[float, float, float]
    active: bool = True


@dataclass
class Interlock:
    name: str
    condition: str
    action: str
    enabled: bool = True
    triggered: bool = False


class SafetyMonitor:
    def __init__(self, limits=None):
        self.level = SafetyLevel.NORMAL
        self.zones: list[SafetyZone] = []
        self.interlocks: list[Interlock] = []
        self.e_stop_pressed = False
        self.e_stop = False
        self.safety_inputs: dict[str, bool] = {}
        self.safety_outputs: dict[str, bool] = {}
        self.event_log: list[dict[str, Any]] = []
        self.watchdog_timeout = 1.0
        self.last_heartbeat = time.time()
        self.limits = limits or {}
        self._last_tick_ok = True
        self._heartbeat = time.time()

    def add_zone(self, zone: SafetyZone):
        self.zones.append(zone)

    def add_interlock(self, interlock: Interlock):
        self.interlocks.append(interlock)

    def set_input(self, name: str, state: bool):
        self.safety_inputs[name] = state

    def get_output(self, name: str) -> bool:
        return self.safety_outputs.get(name, False)

    def set_output(self, name: str, state: bool):
        self.safety_outputs[name] = state

    def check_zone(self, position: tuple[float, float, float]) -> bool:
        for zone in self.zones:
            if not zone.active:
                continue
            if (zone.min_pos[0] <= position[0] <= zone.max_pos[0] and
                zone.min_pos[1] <= position[1] <= zone.max_pos[1] and
                zone.min_pos[2] <= position[2] <= zone.max_pos[2]):
                return True
        return False

    def check_interlocks(self) -> list[Interlock]:
        triggered = []
        for il in self.interlocks:
            if not il.enabled:
                continue
            # evaluate condition (simplified: check safety inputs)
            if self.safety_inputs.get(il.condition):
                il.triggered = True
                triggered.append(il)
                self._execute_action(il.action)
        return triggered

    def _execute_action(self, action: str):
        if action == "e_stop":
            self.emergency_stop()
        elif action == "disable_motion":
            self.set_output("motion_enable", False)
        elif action == "disable_vacuum":
            self.set_output("vacuum_enable", False)

    def emergency_stop(self):
        self.e_stop_pressed = True
        self.e_stop = True
        self.level = SafetyLevel.EMERGENCY
        self.set_output("motion_enable", False)
        self.set_output("vacuum_enable", False)
        self.set_output("spindle_enable", False)
        self.log_event("E-STOP", "Emergency stop activated")

    def reset_e_stop(self) -> bool:
        if self.e_stop_pressed and all(not v for v in self.safety_inputs.values()):
                self.e_stop_pressed = False
                self.e_stop = False
                self.level = SafetyLevel.NORMAL
                self.log_event("RESET", "E-stop reset")
                return True
        return False

    def heartbeat(self):
        self.last_heartbeat = time.time()

    def check_watchdog(self) -> bool:
        if time.time() - self.last_heartbeat > self.watchdog_timeout:
            self.log_event("WATCHDOG", "Watchdog timeout")
            self.emergency_stop()
            return False
        return True

    def set_level(self, level: SafetyLevel):
        self.level = level
        self.log_event("LEVEL", f"Safety level changed to {level.name}")

    def log_event(self, event_type: str, message: str):
        self.event_log.append({"type": event_type, "message": message, "level": self.level.name, "timestamp": time.time()})

    def kick(self):
        self.heartbeat()
        self.last_heartbeat = time.time()
        self._heartbeat = time.time()

    def tick(self, state: dict[str, Any] | None = None) -> bool:
        state = state or {}
        # check limits
        ok = True
        for axis, (lo, hi) in self.limits.items():
            val = state.get(axis, 0)
            if val < lo or val > hi:
                ok = False
                break
        self._last_tick_ok = ok
        if not ok:
            self._trip("limit")
        self.heartbeat()
        return ok

    def ok(self) -> bool:
        return not self.e_stop and self._last_tick_ok

    def trigger_estop(self):
        self.emergency_stop()

    def _trip(self, reason: str):
        self.e_stop = True
        self.e_stop_pressed = True
        self.e_stop = True
        self.level = SafetyLevel.EMERGENCY
        self.log_event("TRIP", reason)

    def get_status(self) -> dict[str, Any]:
        return {
            "level": self.level.name,
            "e_stop": self.e_stop_pressed,
            "inputs": self.safety_inputs,
            "outputs": self.safety_outputs,
            "zones": len(self.zones),
            "interlocks": len(self.interlocks),
            "triggered_interlocks": sum(1 for i in self.interlocks if i.triggered),
            "events": len(self.event_log),
        }

    def is_safe_to_move(self) -> bool:
        return not self.e_stop_pressed and self.level.value < SafetyLevel.ERROR.value

    def is_safe_to_pick(self) -> bool:
        return self.is_safe_to_move() and self.get_output("vacuum_enable")

    def check_speed_limit(self, speed: float, limit: float) -> bool:
        if speed > limit:
            self.log_event("SPEED", f"Speed {speed} exceeds limit {limit}")
            return False
        return True

    def check_force_limit(self, force: float, limit: float) -> bool:
        if abs(force) > limit:
            self.log_event("FORCE", f"Force {force} exceeds limit {limit}")
            return False
        return True
