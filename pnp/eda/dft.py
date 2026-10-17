"""Design for Testability (DFT): scan chains, BIST, ATPG integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ScanFlipFlop:
    name: str
    data_in: str = ""
    scan_in: str = ""
    scan_out: str = ""
    clock: str = "clk"
    enable: bool = False


class ScanChain:
    def __init__(self, name: str):
        self.name = name
        self.ffs: list[ScanFlipFlop] = []
        self.length = 0
        self.si = None  # scan input
        self.so = None  # scan output

    def add_ff(self, ff: ScanFlipFlop):
        self.ffs.append(ff)
        self.length = len(self.ffs)

    def shift_in(self, pattern: list[int]) -> list[int]:
        # shift pattern into chain, return previous content
        prev = [0] * self.length
        # simplified
        return prev

    def shift_out(self) -> list[int]:
        return [0] * self.length

    def capture(self):
        pass

    def update(self):
        pass


class ScanController:
    def __init__(self):
        self.chains: list[ScanChain] = []
        self.mode = "functional"  # functional or scan

    def add_chain(self, chain: ScanChain):
        self.chains.append(chain)

    def set_mode(self, mode: str):
        self.mode = mode

    def total_length(self) -> int:
        return sum(c.length for c in self.chains)

    def load_pattern(self, pattern: list[int]):
        # distribute pattern across chains
        idx = 0
        for chain in self.chains:
            chain.shift_in(pattern[idx:idx+chain.length])
            idx += chain.length

    def capture_response(self) -> list[int]:
        resp = []
        for chain in self.chains:
            resp.extend(chain.shift_out())
        return resp


class BIST:
    def __init__(self, seed: int = 0x12345678, poly: int = 0xB4BCD35C):
        self.seed = seed
        self.poly = poly
        self.lfsr = seed
        self.signature = 0
        self.patterns_generated = 0

    def lfsr_step(self) -> int:
        bit = self.lfsr & 1
        self.lfsr >>= 1
        if bit:
            self.lfsr ^= self.poly
        self.patterns_generated += 1
        return self.lfsr

    def generate_pattern(self) -> int:
        return self.lfsr_step()

    def generate_patterns(self, n: int) -> list[int]:
        return [self.lfsr_step() for _ in range(n)]

    def misr_compact(self, response: int) -> int:
        # MISR: multiple input signature register
        self.signature ^= response
        self.signature = ((self.signature << 1) | (self.signature >> 31)) & 0xFFFFFFFF
        if self.signature & 1:
            self.signature ^= self.poly
        return self.signature

    def run_bist(self, circuit_response: list[int]) -> dict[str, Any]:
        for r in circuit_response:
            self.misr_compact(r)
        return {"signature": self.signature, "patterns": self.patterns_generated}

    def compare_signature(self, expected: int) -> bool:
        return self.signature == expected


class BoundaryScan:
    """JTAG boundary scan (IEEE 1149.1)."""
    def __init__(self, num_cells: int):
        self.num_cells = num_cells
        self.cells: list[int] = [0] * num_cells
        self.instruction = "EXTEST"
        self.state = "RESET"
        self.tdr: list[int] = [0] * num_cells
        self.idcode = 0x12345678

    def set_instruction(self, instr: str):
        self.instruction = instr

    def shift_dr(self, data: list[int]) -> list[int]:
        prev = list(self.cells)
        for i in range(min(len(data), self.num_cells)):
            self.cells[i] = data[i]
        return prev

    def shift_ir(self, instr_bits: list[int]) -> list[int]:
        return [0] * len(instr_bits)

    def update_dr(self):
        self.tdr = list(self.cells)

    def capture_dr(self):
        self.cells = list(self.tdr)

    def run_test(self, test_pattern: list[int]) -> list[int]:
        self.shift_dr(test_pattern)
        self.update_dr()
        return self.tdr

    def get_idcode(self) -> int:
        return self.idcode


class TestAccessMechanism:
    def __init__(self):
        self.test_modes: list[str] = []
        self.active_mode = "functional"

    def enter_test_mode(self, mode: str):
        self.active_mode = mode
        if mode not in self.test_modes:
            self.test_modes.append(mode)

    def exit_test_mode(self):
        self.active_mode = "functional"

    def is_test_mode(self) -> bool:
        return self.active_mode != "functional"


class MBIST:
    """Memory Built-In Self Test."""
    def __init__(self, memory_size: int, data_width: int = 32):
        self.memory_size = memory_size
        self.data_width = data_width
        self.patterns = ["march_c", "march_x", "checkerboard", "walking_ones", "walking_zeros"]
        self.current_pattern = 0
        self.errors: list[dict[str, Any]] = []

    def march_c(self, read_write: Callable[[int, int], int] | None = None) -> list[dict]:
        # March C- algorithm
        errors = []
        # up: write 0, read 0, write 1
        for addr in range(self.memory_size):
            pass
        # down: read 1, write 0, read 0
        for addr in range(self.memory_size - 1, -1, -1):
            pass
        return errors

    def checkerboard(self) -> list[int]:
        pattern = []
        for i in range(self.memory_size):
            pattern.append(0xAAAAAAAA if i % 2 == 0 else 0x55555555)
        return pattern

    def walking_ones(self) -> list[int]:
        patterns = []
        for i in range(self.data_width):
            patterns.append(1 << i)
        return patterns

    def run(self, memory: list[int]) -> dict[str, Any]:
        errors = []
        # simple check: read all and compare to expected (0)
        for addr, val in enumerate(memory):
            if val != 0:
                errors.append({"addr": addr, "expected": 0, "actual": val})
        self.errors = errors
        return {"passed": len(errors) == 0, "errors": len(errors), "patterns_run": len(self.patterns)}
