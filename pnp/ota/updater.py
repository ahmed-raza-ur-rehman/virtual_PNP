"""OTA firmware updater."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class UpdatePackage:
    version: str
    url: str
    size: int
    checksum: str
    signature: str = ""
    release_notes: str = ""
    min_version: str = ""
    mandatory: bool = False


class OTAUpdater:
    def __init__(self, current_version: str, storage_path: str = "/tmp/ota"):
        self.current_version = current_version
        self.storage_path = storage_path
        self.available_updates: list[UpdatePackage] = []
        self.download_progress = 0.0
        self.state = "idle"  # idle, checking, downloading, verifying, installing, complete, error
        self.error_message = ""
        self.update_history: list[dict[str, Any]] = []

    def check_for_updates(self, server_url: str) -> list[UpdatePackage]:
        self.state = "checking"
        # simulated: return a mock update
        self.state = "idle"
        return self.available_updates

    def add_available_update(self, pkg: UpdatePackage):
        self.available_updates.append(pkg)

    def download(self, pkg: UpdatePackage) -> bool:
        self.state = "downloading"
        # simulate download
        for i in range(101):
            self.download_progress = i / 100.0
        self.state = "verifying"
        return True

    def verify(self, pkg: UpdatePackage, data: bytes) -> bool:
        self.state = "verifying"
        calc = hashlib.sha256(data).hexdigest()
        if calc != pkg.checksum:
            self.state = "error"
            self.error_message = "Checksum mismatch"
            return False
        self.state = "idle"
        return True

    def install(self, pkg: UpdatePackage) -> bool:
        self.state = "installing"
        # simulate install
        self.current_version = pkg.version
        self.update_history.append({"version": pkg.version, "timestamp": time.time(), "status": "success"})
        self.state = "complete"
        return True

    def rollback(self) -> bool:
        if len(self.update_history) < 2:
            return False
        prev = self.update_history[-2]["version"]
        self.current_version = prev
        self.state = "idle"
        return True

    def get_status(self) -> dict[str, Any]:
        return {
            "current_version": self.current_version,
            "state": self.state,
            "progress": self.download_progress,
            "error": self.error_message,
            "available_updates": len(self.available_updates),
            "history": self.update_history,
        }

    def compare_versions(self, v1: str, v2: str) -> int:
        # returns -1 if v1<v2, 0 if equal, 1 if v1>v2
        a = [int(x) for x in v1.split(".")]
        b = [int(x) for x in v2.split(".")]
        for i in range(max(len(a), len(b))):
            ai = a[i] if i < len(a) else 0
            bi = b[i] if i < len(b) else 0
            if ai < bi:
                return -1
            if ai > bi:
                return 1
        return 0

    def is_update_available(self) -> bool:
        for pkg in self.available_updates:
            if self.compare_versions(pkg.version, self.current_version) > 0:
                return True
        return False
