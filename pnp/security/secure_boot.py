"""Secure boot and cryptographic verification."""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any


@dataclass
class KeyPair:
    private_key: bytes
    public_key: bytes
    algorithm: str = "RSA-2048"


class SecureBoot:
    def __init__(self):
        self.trusted_keys: list[bytes] = []
        self.revoked_keys: list[bytes] = []
        self.boot_stages: list[str] = ["ROM", "bootloader", "kernel", "application"]
        self.current_stage = "ROM"
        self.verified = False

    def add_trusted_key(self, key: bytes):
        if key not in self.trusted_keys:
            self.trusted_keys.append(key)

    def revoke_key(self, key: bytes):
        if key in self.trusted_keys:
            self.trusted_keys.remove(key)
        self.revoked_keys.append(key)

    def verify_signature(self, data: bytes, signature: bytes, public_key: bytes) -> bool:
        if public_key in self.revoked_keys:
            return False
        if public_key not in self.trusted_keys:
            return False
        # simplified: check HMAC
        expected = hmac.new(public_key, data, hashlib.sha256).digest()
        return hmac.compare_digest(expected, signature)

    def verify_hash(self, data: bytes, expected_hash: bytes) -> bool:
        return hashlib.sha256(data).digest() == expected_hash

    def advance_stage(self, stage: str, image: bytes, signature: bytes, key: bytes) -> bool:
        if stage not in self.boot_stages:
            return False
        if not self.verify_signature(image, signature, key):
            return False
        self.current_stage = stage
        self.verified = True
        return True

    def is_secure(self) -> bool:
        return self.verified and self.current_stage == self.boot_stages[-1]

    def get_status(self) -> dict[str, Any]:
        return {
            "current_stage": self.current_stage,
            "verified": self.verified,
            "trusted_keys": len(self.trusted_keys),
            "revoked_keys": len(self.revoked_keys),
        }


class CryptoEngine:
    def __init__(self):
        self.algorithm = "AES-256-GCM"

    def encrypt(self, plaintext: bytes, key: bytes, iv: bytes) -> bytes:
        # simplified XOR (not real crypto)
        out = bytearray()
        for i, b in enumerate(plaintext):
            out.append(b ^ key[i % len(key)])
        return bytes(out)

    def decrypt(self, ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
        return self.encrypt(ciphertext, key, iv)  # XOR symmetric

    def hash(self, data: bytes, algorithm: str = "sha256") -> str:
        h = hashlib.new(algorithm)
        h.update(data)
        return h.hexdigest()

    def hmac(self, data: bytes, key: bytes, algorithm: str = "sha256") -> str:
        return hmac.new(key, data, algorithm).hexdigest()

    def generate_key(self, length: int = 32) -> bytes:
        import os
        return os.urandom(length)

    def generate_iv(self, length: int = 16) -> bytes:
        import os
        return os.urandom(length)

    def sign(self, data: bytes, private_key: bytes) -> bytes:
        return hmac.new(private_key, data, hashlib.sha256).digest()

    def verify(self, data: bytes, signature: bytes, public_key: bytes) -> bool:
        expected = hmac.new(public_key, data, hashlib.sha256).digest()
        return hmac.compare_digest(expected, signature)


class AuditLog:
    def __init__(self):
        self.entries: list[dict[str, Any]] = []

    def log(self, action: str, user: str, details: dict[str, Any] | None = None):
        import time
        self.entries.append({"action": action, "user": user, "details": details or {}, "timestamp": time.time()})

    def query(self, user: str | None = None, action: str | None = None) -> list[dict[str, Any]]:
        out = self.entries
        if user:
            out = [e for e in out if e["user"] == user]
        if action:
            out = [e for e in out if e["action"] == action]
        return out

    def export(self) -> str:
        import json
        return json.dumps(self.entries, indent=2)


def sign_firmware(data: bytes, key: bytes) -> bytes:
    import hashlib
    import hmac
    return hmac.new(key, data, hashlib.sha256).digest()


def verify_firmware(data: bytes, key: bytes, sig: bytes) -> bool:
    import hashlib
    import hmac
    expected = hmac.new(key, data, hashlib.sha256).digest()
    return hmac.compare_digest(expected, sig)
