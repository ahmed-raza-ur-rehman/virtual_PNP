"""Power management unit (PMU) emulation."""
from __future__ import annotations

from typing import Any


class PowerManager:
    def __init__(self):
        self.voltage_domains: dict[str, float] = {"core": 1.2, "io": 3.3, "analog": 3.3, "backup": 1.8}
        self.power_modes: list[str] = ["run", "sleep", "stop", "standby", "shutdown"]
        self.current_mode = "run"
        self.regulators: dict[str, bool] = {"main": True, "low_power": False}
        self.battery_voltage = 3.3
        self.battery_percent = 100.0
        self.charging = False
        self.wakeup_sources: list[str] = []
        self.power_consumption_mw = 100.0

    def set_mode(self, mode: str):
        if mode in self.power_modes:
            self.current_mode = mode
            self._update_consumption()

    def _update_consumption(self):
        base = {"run": 100.0, "sleep": 10.0, "stop": 1.0, "standby": 0.1, "shutdown": 0.01}
        self.power_consumption_mw = base.get(self.current_mode, 100.0)

    def set_voltage(self, domain: str, voltage: float):
        self.voltage_domains[domain] = voltage

    def get_voltage(self, domain: str) -> float:
        return self.voltage_domains.get(domain, 0.0)

    def enable_regulator(self, reg: str):
        self.regulators[reg] = True

    def disable_regulator(self, reg: str):
        self.regulators[reg] = False

    def add_wakeup_source(self, source: str):
        if source not in self.wakeup_sources:
            self.wakeup_sources.append(source)

    def remove_wakeup_source(self, source: str):
        if source in self.wakeup_sources:
            self.wakeup_sources.remove(source)

    def update_battery(self, voltage: float, charging: bool = False):
        self.battery_voltage = voltage
        self.battery_percent = (voltage - 3.0) / (4.2 - 3.0) * 100.0
        self.battery_percent = max(0.0, min(100.0, self.battery_percent))
        self.charging = charging

    def estimate_runtime_hours(self) -> float:
        if self.power_consumption_mw <= 0:
            return float("inf")
        # assume 1000 mAh battery
        capacity_mah = 1000.0
        hours = capacity_mah / (self.power_consumption_mw / self.voltage_domains.get("core", 3.3))
        return hours

    def get_status(self) -> dict[str, Any]:
        return {
            "mode": self.current_mode,
            "voltages": self.voltage_domains,
            "regulators": self.regulators,
            "battery_voltage": self.battery_voltage,
            "battery_percent": self.battery_percent,
            "charging": self.charging,
            "consumption_mw": self.power_consumption_mw,
            "wakeup_sources": self.wakeup_sources,
            "estimated_runtime_h": self.estimate_runtime_hours(),
        }
