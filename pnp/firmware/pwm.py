"""PWM controller emulation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PWMChannel:
    id: int
    frequency: float = 1000.0
    duty: float = 0.0  # 0..1
    resolution: int = 10  # bits
    enabled: bool = False
    polarity: str = "high"  # high or low
    dead_time: int = 0
    phase: float = 0.0

    def set_frequency(self, freq: float):
        self.frequency = freq

    def set_duty(self, duty: float):
        self.duty = max(0.0, min(1.0, duty))

    def set_duty_percent(self, percent: float):
        self.set_duty(percent / 100.0)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def get_period_ticks(self, clock_hz: float) -> int:
        if self.frequency <= 0:
            return 0
        return int(clock_hz / self.frequency)

    def get_compare_value(self) -> int:
        max_val = (1 << self.resolution) - 1
        return int(self.duty * max_val)

    def output_level(self, phase: float) -> int:
        if not self.enabled:
            return 0
        level = 1 if (phase % 1.0) < self.duty else 0
        if self.polarity == "low":
            level ^= 1
        return level


class PWMController:
    def __init__(self, channels: int = 8, clock_hz: float = 72_000_000):
        self.clock_hz = clock_hz
        self.channels: list[PWMChannel] = [PWMChannel(id=i) for i in range(channels)]

    def get_channel(self, ch: int) -> PWMChannel:
        return self.channels[ch]

    def set_frequency(self, ch: int, freq: float):
        self.channels[ch].set_frequency(freq)

    def set_duty(self, ch: int, duty: float):
        self.channels[ch].set_duty(duty)

    def enable(self, ch: int):
        self.channels[ch].enable()

    def disable(self, ch: int):
        self.channels[ch].disable()

    def get_status(self) -> dict[str, Any]:
        return {
            "clock_hz": self.clock_hz,
            "channels": [{"id": c.id, "freq": c.frequency, "duty": c.duty, "enabled": c.enabled} for c in self.channels],
        }

    def generate_waveform(self, ch: int, samples: int = 1000) -> list[int]:
        c = self.channels[ch]
        out = []
        for i in range(samples):
            phase = (i / samples) * c.frequency
            out.append(c.output_level(phase))
        return out
