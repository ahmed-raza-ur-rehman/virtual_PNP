"""Telemetry collection and export."""
from __future__ import annotations

import time
from collections import deque


class Telemetry:
    def __init__(self, maxlen=1000):
        self.samples = deque(maxlen=maxlen)

    def record(self, **kwargs):
        self.samples.append({"t": time.time(), **kwargs})

    def latest(self):
        return self.samples[-1] if self.samples else None

    def to_list(self):
        return list(self.samples)
