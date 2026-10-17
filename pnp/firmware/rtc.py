"""Real-Time Clock (RTC) emulation."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class RTCAlarm:
    hour: int = 0
    minute: int = 0
    second: int = 0
    enabled: bool = False
    triggered: bool = False


class RTC:
    def __init__(self, initial_unix: int | None = None):
        self.unix_time = initial_unix if initial_unix is not None else int(time.time())
        self.alarms: list[RTCAlarm] = []
        self.wakeup_enabled = False
        self.wakeup_period = 0
        self.calibration = 0
        self.backup_registers: list[int] = [0] * 20
        self.format_24h = True
        self.running = True

    def get_time(self) -> dict[str, int]:
        t = self.unix_time
        sec = t % 60
        minute = (t // 60) % 60
        hour = (t // 3600) % 24
        day = (t // 86400) % 31 + 1
        month = ((t // 2629746) % 12) + 1
        year = 1970 + t // 31556952
        return {"year": year, "month": month, "day": day, "hour": hour, "minute": minute, "second": sec, "unix": t}

    def set_time(self, unix: int):
        self.unix_time = unix

    def set_time_fields(self, year, month, day, hour, minute, second):
        # approximate
        import datetime
        dt = datetime.datetime(year, month, day, hour, minute, second)
        self.unix_time = int(dt.timestamp())

    def tick(self, seconds: int = 1):
        self.unix_time += seconds
        self._check_alarms()

    def add_alarm(self, alarm: RTCAlarm):
        self.alarms.append(alarm)

    def _check_alarms(self):
        t = self.get_time()
        for a in self.alarms:
            if a.enabled and t["hour"] == a.hour and t["minute"] == a.minute and t["second"] == a.second:
                a.triggered = True

    def get_triggered_alarms(self) -> list[RTCAlarm]:
        return [a for a in self.alarms if a.triggered]

    def clear_alarm(self, alarm: RTCAlarm):
        alarm.triggered = False

    def enable_wakeup(self, period: int):
        self.wakeup_enabled = True
        self.wakeup_period = period

    def disable_wakeup(self):
        self.wakeup_enabled = False

    def write_backup(self, idx: int, val: int):
        if idx < len(self.backup_registers):
            self.backup_registers[idx] = val

    def read_backup(self, idx: int) -> int:
        if idx < len(self.backup_registers):
            return self.backup_registers[idx]
        return 0

    def calibrate(self, ppm: int):
        self.calibration = ppm

    def get_status(self) -> dict[str, Any]:
        return {"time": self.get_time(), "alarms": len(self.alarms), "running": self.running,
                "wakeup": self.wakeup_enabled, "calibration_ppm": self.calibration}
