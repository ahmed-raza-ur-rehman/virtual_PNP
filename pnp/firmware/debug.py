"""Debug interface (SWD/JTAG) emulation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Breakpoint:
    address: int
    enabled: bool = True
    hit_count: int = 0
    kind: str = "hardware"  # hardware, software


class DebugInterface:
    def __init__(self):
        self.connected = False
        self.halted = False
        self.breakpoints: list[Breakpoint] = []
        self.watchpoints: list[dict[str, Any]] = []
        self.registers: dict[str, int] = {}
        self.memory: bytearray = bytearray(1024 * 1024)
        self.trace_enabled = False
        self.trace_buffer: list[dict[str, Any]] = []
        self.step_mode = False

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False
        self.halted = False

    def halt(self):
        self.halted = True

    def resume(self):
        self.halted = False

    def step(self) -> int:
        # returns PC after step
        return self.registers.get("PC", 0) + 4

    def reset(self):
        self.registers["PC"] = 0
        self.halted = False

    def read_register(self, name: str) -> int:
        return self.registers.get(name, 0)

    def write_register(self, name: str, value: int):
        self.registers[name] = value

    def read_memory(self, addr: int, length: int) -> bytes:
        return bytes(self.memory[addr:addr + length])

    def write_memory(self, addr: int, data: bytes):
        self.memory[addr:addr + len(data)] = data

    def add_breakpoint(self, addr: int, kind: str = "hardware") -> Breakpoint:
        bp = Breakpoint(address=addr, kind=kind)
        self.breakpoints.append(bp)
        return bp

    def remove_breakpoint(self, addr: int):
        self.breakpoints = [b for b in self.breakpoints if b.address != addr]

    def enable_breakpoint(self, addr: int):
        for b in self.breakpoints:
            if b.address == addr:
                b.enabled = True

    def disable_breakpoint(self, addr: int):
        for b in self.breakpoints:
            if b.address == addr:
                b.enabled = False

    def add_watchpoint(self, addr: int, size: int, access: str = "rw"):
        self.watchpoints.append({"addr": addr, "size": size, "access": access, "hits": 0})

    def remove_watchpoint(self, addr: int):
        self.watchpoints = [w for w in self.watchpoints if w["addr"] != addr]

    def trace_enable(self, enable: bool = True):
        self.trace_enabled = enable
        if not enable:
            self.trace_buffer.clear()

    def trace_record(self, event: dict[str, Any]):
        if self.trace_enabled:
            self.trace_buffer.append(event)
            if len(self.trace_buffer) > 10000:
                self.trace_buffer.pop(0)

    def get_status(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "halted": self.halted,
            "breakpoints": len(self.breakpoints),
            "watchpoints": len(self.watchpoints),
            "trace_enabled": self.trace_enabled,
            "trace_size": len(self.trace_buffer),
        }
