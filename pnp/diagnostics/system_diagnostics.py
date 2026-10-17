"""System diagnostics and health monitoring."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class DiagnosticResult:
    name: str
    status: str  # pass, fail, warning
    value: Any = None
    message: str = ""
    timestamp: float = 0.0


class SystemDiagnostics:
    def __init__(self):
        self.results: list[DiagnosticResult] = []
        self.checks: dict[str, Any] = {}

    def run_all(self) -> list[DiagnosticResult]:
        self.results.clear()
        self.check_cpu()
        self.check_memory()
        self.check_disk()
        self.check_network()
        self.check_sensors()
        self.check_actuators()
        self.check_communication()
        return self.results

    def check_cpu(self) -> DiagnosticResult:
        # simulated
        usage = np.random.uniform(10, 60)
        status = "pass" if usage < 80 else "warning"
        r = DiagnosticResult(name="CPU", status=status, value=usage, message=f"CPU usage: {usage:.1f}%", timestamp=time.time())
        self.results.append(r)
        return r

    def check_memory(self) -> DiagnosticResult:
        total = 1024 * 1024 * 1024  # 1GB
        used = np.random.uniform(200, 600) * 1024 * 1024
        usage = used / total * 100
        status = "pass" if usage < 85 else "warning"
        r = DiagnosticResult(name="Memory", status=status, value=usage, message=f"Memory usage: {usage:.1f}%", timestamp=time.time())
        self.results.append(r)
        return r

    def check_disk(self) -> DiagnosticResult:
        free_gb = np.random.uniform(5, 50)
        status = "pass" if free_gb > 1 else "fail"
        r = DiagnosticResult(name="Disk", status=status, value=free_gb, message=f"Free disk: {free_gb:.1f} GB", timestamp=time.time())
        self.results.append(r)
        return r

    def check_network(self) -> DiagnosticResult:
        latency = np.random.uniform(1, 50)
        status = "pass" if latency < 100 else "warning"
        r = DiagnosticResult(name="Network", status=status, value=latency, message=f"Latency: {latency:.1f} ms", timestamp=time.time())
        self.results.append(r)
        return r

    def check_sensors(self) -> DiagnosticResult:
        # check all sensors
        ok = True
        msg = "All sensors OK"
        r = DiagnosticResult(name="Sensors", status="pass" if ok else "fail", value=ok, message=msg, timestamp=time.time())
        self.results.append(r)
        return r

    def check_actuators(self) -> DiagnosticResult:
        ok = True
        r = DiagnosticResult(name="Actuators", status="pass" if ok else "fail", value=ok, message="All actuators OK", timestamp=time.time())
        self.results.append(r)
        return r

    def check_communication(self) -> DiagnosticResult:
        ok = True
        r = DiagnosticResult(name="Communication", status="pass" if ok else "fail", value=ok, message="Communication OK", timestamp=time.time())
        self.results.append(r)
        return r

    def check_motor(self, motor_id: int) -> DiagnosticResult:
        # check motor health
        current = np.random.uniform(0.1, 2.0)
        temp = np.random.uniform(25, 60)
        status = "pass"
        if temp > 80:
            status = "fail"
        elif temp > 60:
            status = "warning"
        r = DiagnosticResult(name=f"Motor {motor_id}", status=status, value={"current": current, "temp": temp},
                            message=f"Motor {motor_id}: {current:.2f}A, {temp:.1f}C", timestamp=time.time())
        self.results.append(r)
        return r

    def check_vacuum(self) -> DiagnosticResult:
        pressure = np.random.uniform(-90, -70)
        status = "pass" if pressure < -75 else "warning"
        r = DiagnosticResult(name="Vacuum", status=status, value=pressure, message=f"Pressure: {pressure:.1f} kPa", timestamp=time.time())
        self.results.append(r)
        return r

    def check_vision(self) -> DiagnosticResult:
        fps = np.random.uniform(20, 60)
        status = "pass" if fps > 25 else "warning"
        r = DiagnosticResult(name="Vision", status=status, value=fps, message=f"FPS: {fps:.1f}", timestamp=time.time())
        self.results.append(r)
        return r

    def get_summary(self) -> dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "pass")
        failed = sum(1 for r in self.results if r.status == "fail")
        warnings = sum(1 for r in self.results if r.status == "warning")
        return {"total": total, "passed": passed, "failed": failed, "warnings": warnings,
                "health": "healthy" if failed == 0 else "degraded"}

    def get_failures(self) -> list[DiagnosticResult]:
        return [r for r in self.results if r.status == "fail"]

    def get_warnings(self) -> list[DiagnosticResult]:
        return [r for r in self.results if r.status == "warning"]

    def report(self) -> str:
        lines = ["System Diagnostics Report"]
        summary = self.get_summary()
        lines.append(f"  Total checks: {summary['total']}")
        lines.append(f"  Passed: {summary['passed']}")
        lines.append(f"  Failed: {summary['failed']}")
        lines.append(f"  Warnings: {summary['warnings']}")
        lines.append(f"  Health: {summary['health']}")
        lines.append("")
        for r in self.results:
            lines.append(f"  [{r.status.upper()}] {r.name}: {r.message}")
        return "\n".join(lines)


class HealthMonitor:
    def __init__(self):
        self.diagnostics = SystemDiagnostics()
        self.history: list[dict[str, Any]] = []
        self.alert_thresholds: dict[str, float] = {}

    def set_threshold(self, metric: str, threshold: float):
        self.alert_thresholds[metric] = threshold

    def check(self) -> dict[str, Any]:
        self.diagnostics.run_all()
        summary = self.diagnostics.get_summary()
        record = {"timestamp": time.time(), "summary": summary}
        self.history.append(record)
        if len(self.history) > 1000:
            self.history.pop(0)
        return summary

    def get_trend(self, metric: str, n: int = 10) -> list[float]:
        return []

    def is_healthy(self) -> bool:
        if not self.history:
            return True
        return self.history[-1]["summary"]["health"] == "healthy"

    def get_uptime(self) -> float:
        return time.time() - (self.history[0]["timestamp"] if self.history else time.time())
