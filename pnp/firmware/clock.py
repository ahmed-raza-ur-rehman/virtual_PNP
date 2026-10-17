"""Clock management unit (CMU) emulation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ClockSource:
    name: str
    frequency: int
    enabled: bool = False
    stable: bool = False
    accuracy_ppm: int = 0


class ClockManager:
    def __init__(self):
        self.sources: dict[str, ClockSource] = {}
        self.plls: dict[str, dict[str, Any]] = {}
        self.muxes: dict[str, str] = {}
        self.dividers: dict[str, int] = {}
        self.gates: dict[str, bool] = {}
        self._init_defaults()

    def _init_defaults(self):
        self.sources["HSI"] = ClockSource("HSI", 16_000_000, True, True, 10000)
        self.sources["HSE"] = ClockSource("HSE", 8_000_000, False, False, 50)
        self.sources["LSI"] = ClockSource("LSI", 32000, True, True, 50000)
        self.sources["LSE"] = ClockSource("LSE", 32768, False, False, 20)
        self.muxes["SYSCLK"] = "HSI"
        self.dividers["AHB"] = 1
        self.dividers["APB1"] = 2
        self.dividers["APB2"] = 1

    def enable_source(self, name: str):
        if name in self.sources:
            self.sources[name].enabled = True
            self.sources[name].stable = True

    def disable_source(self, name: str):
        if name in self.sources:
            self.sources[name].enabled = False
            self.sources[name].stable = False

    def configure_pll(self, name: str, src: str, mul: int, div: int):
        base = self.sources.get(src)
        if base is None:
            return
        freq = base.frequency * mul // div
        self.plls[name] = {"src": src, "mul": mul, "div": div, "freq": freq, "enabled": False, "locked": False}

    def enable_pll(self, name: str):
        if name in self.plls:
            self.plls[name]["enabled"] = True
            self.plls[name]["locked"] = True

    def set_sysclk_mux(self, source: str):
        if source in self.sources or source in self.plls:
            self.muxes["SYSCLK"] = source

    def set_divider(self, bus: str, div: int):
        self.dividers[bus] = div

    def enable_clock_gate(self, periph: str):
        self.gates[periph] = True

    def disable_clock_gate(self, periph: str):
        self.gates[periph] = False

    def get_sysclk(self) -> int:
        src = self.muxes.get("SYSCLK", "HSI")
        if src in self.plls:
            return self.plls[src]["freq"]
        if src in self.sources:
            return self.sources[src].frequency
        return 0

    def get_hclk(self) -> int:
        return self.get_sysclk() // self.dividers.get("AHB", 1)

    def get_pclk1(self) -> int:
        return self.get_hclk() // self.dividers.get("APB1", 1)

    def get_pclk2(self) -> int:
        return self.get_hclk() // self.dividers.get("APB2", 1)

    def get_status(self) -> dict[str, Any]:
        return {
            "sysclk": self.get_sysclk(),
            "hclk": self.get_hclk(),
            "pclk1": self.get_pclk1(),
            "pclk2": self.get_pclk2(),
            "mux": self.muxes.get("SYSCLK"),
            "sources": {k: {"freq": v.frequency, "enabled": v.enabled, "stable": v.stable} for k, v in self.sources.items()},
            "plls": self.plls,
            "dividers": self.dividers,
            "gates": self.gates,
        }
