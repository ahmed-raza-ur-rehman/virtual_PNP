"""Secure boot and firmware signing utilities."""
from __future__ import annotations

import hashlib
import hmac


def sign_firmware(data: bytes, key: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def verify_firmware(data: bytes, key: bytes, signature: bytes) -> bool:
    return hmac.compare_digest(sign_firmware(data, key), signature)
