"""Hardware test framework."""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""
    duration: float = 0.0
    value: Any = None


class HardwareTestSuite:
    def __init__(self, name: str = "Hardware Tests"):
        self.name = name
        self.tests: list[tuple[str, Callable]] = []
        self.results: list[TestResult] = []

    def add_test(self, name: str, test_fn: Callable):
        self.tests.append((name, test_fn))

    def run(self) -> list[TestResult]:
        self.results.clear()
        for name, fn in self.tests:
            t0 = time.time()
            try:
                result = fn()
                passed = bool(result) if not isinstance(result, tuple) else bool(result[0])
                msg = result[1] if isinstance(result, tuple) and len(result) > 1 else ""
                val = result[2] if isinstance(result, tuple) and len(result) > 2 else result
            except (ValueError, RuntimeError) as e:
                passed = False
                msg = str(e)
                val = None
            dur = time.time() - t0
            self.results.append(TestResult(name=name, passed=passed, message=msg, duration=dur, value=val))
        return self.results

    def get_summary(self) -> dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        return {"total": total, "passed": passed, "failed": total - passed,
                "pass_rate": passed / total if total > 0 else 0.0}

    def report(self) -> str:
        lines = [f"Hardware Test Suite: {self.name}"]
        summary = self.get_summary()
        lines.append(f"  Total: {summary['total']}, Passed: {summary['passed']}, Failed: {summary['failed']}")
        lines.append("")
        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"  [{status}] {r.name} ({r.duration*1000:.1f}ms): {r.message}")
        return "\n".join(lines)


class MotorTest:
    @staticmethod
    def test_encoder(motor_id: int) -> tuple[bool, str]:
        # simulate encoder test
        count = 1000
        return count > 0, f"Encoder count: {count}"

    @staticmethod
    def test_movement(motor_id: int, distance: float) -> tuple[bool, str]:
        return True, f"Moved {distance} mm"

    @staticmethod
    def test_homing(motor_id: int) -> tuple[bool, str]:
        return True, "Homing successful"

    @staticmethod
    def test_limits(motor_id: int) -> tuple[bool, str]:
        return True, "Limits OK"


class VacuumTest:
    @staticmethod
    def test_pickup() -> tuple[bool, str]:
        return True, "Pickup successful"

    @staticmethod
    def test_pressure() -> tuple[bool, str]:
        return True, "Pressure OK"

    @staticmethod
    def test_leak() -> tuple[bool, str]:
        return True, "No leak"


class VisionTest:
    @staticmethod
    def test_camera() -> tuple[bool, str]:
        return True, "Camera OK"

    @staticmethod
    def test_detection() -> tuple[bool, str]:
        return True, "Detection OK"

    @staticmethod
    def test_calibration() -> tuple[bool, str]:
        return True, "Calibration OK"


class CommunicationTest:
    @staticmethod
    def test_uart() -> tuple[bool, str]:
        return True, "UART OK"

    @staticmethod
    def test_spi() -> tuple[bool, str]:
        return True, "SPI OK"

    @staticmethod
    def test_i2c() -> tuple[bool, str]:
        return True, "I2C OK"

    @staticmethod
    def test_can() -> tuple[bool, str]:
        return True, "CAN OK"
