"""OTA firmware update."""
from __future__ import annotations

import os


class OTAUpdater:
    def __init__(self, firmware_path: str):
        self.firmware_path = firmware_path

    def check_update(self) -> bool:
        return os.path.exists(self.firmware_path + ".new")

    def apply_update(self) -> bool:
        if self.check_update():
            os.replace(self.firmware_path + ".new", self.firmware_path)
            return True
        return False
