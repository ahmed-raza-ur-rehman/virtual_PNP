"""Safety monitoring: soft limits, watchdog, e-stop latching, violation log.

Design notes
------------
The monitor is deliberately transport-agnostic: the machine controller polls
:meth:`SafetyMonitor.tick` every control cycle and the HMI/PLC layer reacts to
:attr:`SafetyMonitor.e_stop`.  All violations are latched so that a transient
fault cannot be silently masked by a subsequent good reading -- mirroring the
behaviour required by IEC 60204-1 emergency-stop categories.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class SafetyMonitor:
    """Latching safety supervisor for the pick-and-place machine."""

    limits: dict[str, tuple[float, float]] = field(default_factory=dict)
    watchdog_timeout_s: float = 1.0
    max_violations: int = 256
    _last_kick: float = field(default_factory=time.monotonic)
    e_stop: bool = False
    violations: list[str] = field(default_factory=list)

    def kick(self) -> None:
        """Feed the watchdog (called by the healthy control loop)."""
        self._last_kick = time.monotonic()

    def check_watchdog(self) -> bool:
        if time.monotonic() - self._last_kick > self.watchdog_timeout_s:
            self._trip("watchdog_timeout")
            return False
        return True

    def check_limits(self, pos: dict[str, float]) -> bool:
        for axis, (lo, hi) in self.limits.items():
            v = float(pos.get(axis, 0.0))
            if v < lo or v > hi:
                self._trip(f"limit_{axis}")
                return False
        return True

    def tick(self, pos: dict[str, float] | None = None) -> bool:
        """One safety cycle. Returns True when the machine may keep moving."""
        if not self.check_watchdog():
            return False
        if pos is not None and not self.check_limits(pos):
            return False
        return not self.e_stop

    def _trip(self, reason: str) -> None:
        self.e_stop = True
        if len(self.violations) < self.max_violations:
            self.violations.append(reason)

    def reset(self, operator: str = "operator") -> None:
        """Manual reset after the fault cause has been removed."""
        self.e_stop = False
        self.violations.clear()
        self.kick()


__all__ = ["SafetyMonitor"]
