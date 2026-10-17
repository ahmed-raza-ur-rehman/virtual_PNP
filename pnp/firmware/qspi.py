"""QSPI / OSPI flash interface emulation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class QSPICommand:
    instruction: int
    address: int = 0
    alt: int = 0
    dummy_cycles: int = 0
    data: bytes = b""
    mode: str = "indirect"  # indirect, memory_mapped, auto_polling
    data_size: int = 0
    sio_mode: int = 1  # 1, 2, 4


class QSPIController:
    def __init__(self, flash_size: int = 16 * 1024 * 1024):
        self.flash_size = flash_size
        self.flash = bytearray(flash_size)
        for i in range(flash_size):
            self.flash[i] = 0xFF
        self.cs = True
        self.clock_hz = 100_000_000
        self.mode = "indirect"
        self.last_status = 0

    def write_enable(self):
        self.last_status |= 0x02

    def write_disable(self):
        self.last_status &= ~0x02

    def read_status(self) -> int:
        return self.last_status

    def erase_sector(self, addr: int, size: int = 4096):
        for i in range(addr, min(addr + size, self.flash_size)):
            self.flash[i] = 0xFF

    def erase_chip(self):
        for i in range(self.flash_size):
            self.flash[i] = 0xFF

    def program_page(self, addr: int, data: bytes):
        for i, b in enumerate(data):
            if addr + i < self.flash_size:
                self.flash[addr + i] &= b

    def read(self, addr: int, length: int) -> bytes:
        return bytes(self.flash[addr:addr + length])

    def memory_map(self, base: int):
        self.mode = "memory_mapped"

    def execute_command(self, cmd: QSPICommand) -> bytes:
        if cmd.instruction == 0x03:  # read
            return self.read(cmd.address, cmd.data_size or len(cmd.data) or 256)
        if cmd.instruction == 0x02:  # page program
            self.write_enable()
            self.program_page(cmd.address, cmd.data)
            return b""
        if cmd.instruction == 0x20:  # sector erase
            self.write_enable()
            self.erase_sector(cmd.address)
            return b""
        if cmd.instruction == 0x05:  # read status
            return bytes([self.last_status])
        return b""

    def get_status(self) -> dict[str, Any]:
        return {"flash_size": self.flash_size, "mode": self.mode, "clock_hz": self.clock_hz, "cs": self.cs}
