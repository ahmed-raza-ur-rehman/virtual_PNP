"""Watchdog timer (WDT) emulation."""
from __future__ import annotations

from typing import Any


class Watchdog:
    def __init__(self, timeout_ms: int = 1000):
        self.timeout_ms = timeout_ms
        self.counter = 0
        self.enabled = False
        self.triggered = False
        self.window_mode = False
        self.window_min = 0
        self.window_max = timeout_ms
        self.early_warning = False
        self.reset_on_timeout = True

    def enable(self, timeout_ms: int | None = None):
        if timeout_ms is not None:
            self.timeout_ms = timeout_ms
        self.enabled = True
        self.counter = 0
        self.triggered = False

    def disable(self):
        self.enabled = False

    def feed(self):
        if self.window_mode and (self.counter < self.window_min or self.counter > self.window_max):
            self.triggered = True
            return
        self.counter = 0
        self.triggered = False

    def tick(self, ms: int = 1):
        if not self.enabled:
            return
        self.counter += ms
        if self.counter >= self.timeout_ms * 0.8 and not self.early_warning:
            self.early_warning = True
        if self.counter >= self.timeout_ms:
            self.triggered = True
            if self.reset_on_timeout:
                pass

    def set_window(self, min_ms: int, max_ms: int):
        self.window_mode = True
        self.window_min = min_ms
        self.window_max = max_ms

    def get_status(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "counter": self.counter, "timeout": self.timeout_ms,
                "triggered": self.triggered, "early_warning": self.early_warning, "window_mode": self.window_mode}
