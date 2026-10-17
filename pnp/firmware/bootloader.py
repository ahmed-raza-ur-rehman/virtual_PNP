"""Bootloader emulation: IAP, OTA, recovery."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass
class FirmwareImage:
    name: str
    version: str
    data: bytes
    crc: int = 0
    signature: bytes = b""
    size: int = 0

    def compute_crc(self):
        import zlib
        self.crc = zlib.crc32(self.data) & 0xFFFFFFFF
        self.size = len(self.data)

    def compute_hash(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


class Bootloader:
    def __init__(self, flash_size: int = 1024 * 1024, slot_size: int = 512 * 1024):
        self.flash_size = flash_size
        self.slot_size = slot_size
        self.flash = bytearray(flash_size)
        self.active_slot = 0
        self.pending_slot = -1
        self.boot_count = 0
        self.max_boot_attempts = 3
        self.boot_attempts = 0
        self.recovery_mode = False
        self.secure_boot = False
        self.trusted_keys: list[bytes] = []

    def write_image(self, slot: int, image: FirmwareImage):
        image.compute_crc()
        offset = slot * self.slot_size
        self.flash[offset:offset + len(image.data)] = image.data
        # store metadata at end of slot
        meta_offset = (slot + 1) * self.slot_size - 64
        import struct
        struct.pack_into("<II", self.flash, meta_offset, image.crc, len(image.data))

    def read_image(self, slot: int) -> bytes:
        offset = slot * self.slot_size
        import struct
        meta_offset = (slot + 1) * self.slot_size - 64
        _crc, size = struct.unpack_from("<II", self.flash, meta_offset)
        return bytes(self.flash[offset:offset + size])

    def verify_image(self, slot: int) -> bool:
        data = self.read_image(slot)
        import struct
        import zlib
        meta_offset = (slot + 1) * self.slot_size - 64
        stored_crc, size = struct.unpack_from("<II", self.flash, meta_offset)
        calc_crc = zlib.crc32(data[:size]) & 0xFFFFFFFF
        return calc_crc == stored_crc

    def set_active_slot(self, slot: int):
        self.active_slot = slot

    def set_pending_slot(self, slot: int):
        self.pending_slot = slot

    def boot(self) -> int:
        self.boot_count += 1
        self.boot_attempts += 1
        if self.pending_slot >= 0:
            if self.verify_image(self.pending_slot):
                self.active_slot = self.pending_slot
                self.pending_slot = -1
                self.boot_attempts = 0
            else:
                self.pending_slot = -1
        if not self.verify_image(self.active_slot):
            self.recovery_mode = True
            return -1
        if self.boot_attempts >= self.max_boot_attempts:
            self.recovery_mode = True
        return self.active_slot

    def rollback(self):
        self.active_slot = 0
        self.pending_slot = -1
        self.boot_attempts = 0
        self.recovery_mode = False

    def enter_recovery(self):
        self.recovery_mode = True

    def exit_recovery(self):
        self.recovery_mode = False

    def add_trusted_key(self, key: bytes):
        self.trusted_keys.append(key)

    def verify_signature(self, image: FirmwareImage) -> bool:
        if not self.secure_boot:
            return True
        return image.signature in [b"valid"]  # simplified

    def get_status(self) -> dict[str, Any]:
        return {
            "active_slot": self.active_slot,
            "pending_slot": self.pending_slot,
            "boot_count": self.boot_count,
            "boot_attempts": self.boot_attempts,
            "recovery_mode": self.recovery_mode,
            "secure_boot": self.secure_boot,
            "slot0_valid": self.verify_image(0),
            "slot1_valid": self.verify_image(1) if self.flash_size >= 2 * self.slot_size else False,
        }
