"""Telemetry and metrics collection."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Metric:
    name: str
    value: float
    timestamp: float = 0.0
    tags: dict[str, str] = field(default_factory=dict)


class TelemetryCollector:
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.metrics: dict[str, deque] = {}
        self.counters: dict[str, float] = {}
        self.gauges: dict[str, float] = {}
        self.histograms: dict[str, list[float]] = {}

    def record(self, name: str, value: float, tags: dict[str, str] | None = None):
        if name not in self.metrics:
            self.metrics[name] = deque(maxlen=self.max_history)
        self.metrics[name].append(Metric(name=name, value=value, timestamp=time.time(), tags=tags or {}))

    def increment(self, name: str, amount: float = 1.0):
        self.counters[name] = self.counters.get(name, 0) + amount

    def gauge(self, name: str, value: float):
        self.gauges[name] = value

    def histogram(self, name: str, value: float):
        self.histograms.setdefault(name, []).append(value)

    def get_latest(self, name: str) -> float | None:
        if self.metrics.get(name):
            return self.metrics[name][-1].value
        return None

    def get_history(self, name: str, n: int = 100) -> list[Metric]:
        if name not in self.metrics:
            return []
        return list(self.metrics[name])[-n:]

    def get_stats(self, name: str) -> dict[str, float]:
        if name not in self.metrics or not self.metrics[name]:
            return {}
        vals = [m.value for m in self.metrics[name]]
        import statistics
        return {
            "count": len(vals),
            "min": min(vals),
            "max": max(vals),
            "mean": statistics.mean(vals),
            "median": statistics.median(vals),
            "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
        }

    def get_histogram_stats(self, name: str) -> dict[str, Any]:
        vals = self.histograms.get(name, [])
        if not vals:
            return {}
        vals_sorted = sorted(vals)
        n = len(vals_sorted)
        return {
            "count": n,
            "min": vals_sorted[0],
            "max": vals_sorted[-1],
            "mean": sum(vals) / n,
            "p50": vals_sorted[n // 2],
            "p95": vals_sorted[int(n * 0.95)],
            "p99": vals_sorted[int(n * 0.99)],
        }

    def export_prometheus(self) -> str:
        lines = []
        for name, vals in self.metrics.items():
            if vals:
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {vals[-1].value}")
        for name, val in self.counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {val}")
        for name, val in self.gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {val}")
        return "\n".join(lines)

    def export_json(self) -> dict[str, Any]:
        return {
            "metrics": {n: [m.value for m in v] for n, v in self.metrics.items()},
            "counters": self.counters,
            "gauges": self.gauges,
        }

    def reset(self):
        self.metrics.clear()
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()


class AlertManager:
    def __init__(self):
        self.rules: list[dict[str, Any]] = []
        self.alerts: list[dict[str, Any]] = []

    def add_rule(self, name: str, metric: str, condition: str, threshold: float, severity: str = "warning"):
        self.rules.append({"name": name, "metric": metric, "condition": condition, "threshold": threshold, "severity": severity})

    def evaluate(self, collector: TelemetryCollector):
        for rule in self.rules:
            val = collector.get_latest(rule["metric"])
            if val is None:
                continue
            triggered = False
            if rule["condition"] == "gt" and val > rule["threshold"] or rule["condition"] == "lt" and val < rule["threshold"] or rule["condition"] == "eq" and val == rule["threshold"]:
                triggered = True
            if triggered:
                self.alerts.append({"rule": rule["name"], "metric": rule["metric"], "value": val,
                                    "threshold": rule["threshold"], "severity": rule["severity"], "time": time.time()})

    def get_active_alerts(self) -> list[dict[str, Any]]:
        return list(self.alerts)

    def clear_alerts(self):
        self.alerts.clear()


class Telemetry:
    def __init__(self):
        self.records = []

    def record(self, **kwargs):
        self.records.append(kwargs)

    def latest(self):
        return self.records[-1] if self.records else {}

    def to_list(self):
        return list(self.records)
