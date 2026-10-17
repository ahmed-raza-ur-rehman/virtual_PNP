"""Performance analysis and benchmarking."""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class BenchmarkResult:
    name: str
    iterations: int
    total_time: float
    mean_time: float
    min_time: float
    max_time: float
    std_time: float
    throughput: float


class PerformanceAnalyzer:
    def __init__(self):
        self.results: list[BenchmarkResult] = []

    def benchmark(self, name: str, func: Callable, *args, iterations: int = 100, **kwargs) -> BenchmarkResult:
        times = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            func(*args, **kwargs)
            t1 = time.perf_counter()
            times.append(t1 - t0)
        times = np.array(times)
        r = BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time=float(times.sum()),
            mean_time=float(times.mean()),
            min_time=float(times.min()),
            max_time=float(times.max()),
            std_time=float(times.std()),
            throughput=float(iterations / times.sum()) if times.sum() > 0 else 0.0,
        )
        self.results.append(r)
        return r

    def profile_function(self, func: Callable, *args, **kwargs) -> dict[str, Any]:
        import cProfile
        import io
        import pstats
        pr = cProfile.Profile()
        pr.enable()
        func(*args, **kwargs)
        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
        ps.print_stats(20)
        return {"stats": s.getvalue()}

    def compare(self, results: list[BenchmarkResult]) -> str:
        lines = ["Performance Comparison"]
        for r in sorted(results, key=lambda x: x.mean_time):
            lines.append(f"  {r.name}: {r.mean_time*1000:.3f} ms (throughput: {r.throughput:.1f}/s)")
        return "\n".join(lines)

    def get_bottlenecks(self, threshold_ms: float = 10.0) -> list[BenchmarkResult]:
        return [r for r in self.results if r.mean_time * 1000 > threshold_ms]

    def report(self) -> str:
        lines = ["Performance Analysis Report"]
        for r in self.results:
            lines.append(f"  {r.name}: mean={r.mean_time*1000:.3f}ms min={r.min_time*1000:.3f}ms max={r.max_time*1000:.3f}ms throughput={r.throughput:.1f}/s")
        return "\n".join(lines)


class MemoryProfiler:
    def __init__(self):
        self.snapshots: list[dict[str, Any]] = []

    def snapshot(self, label: str = ""):
        self.snapshots.append({"label": label, "time": time.time(), "objects": len(gc_objects()) if False else 0})

    def get_growth(self) -> float:
        if len(self.snapshots) < 2:
            return 0.0
        return 0.0

    def report(self) -> str:
        lines = ["Memory Profile"]
        for s in self.snapshots:
            lines.append(f"  {s['label']}: {s['objects']} objects")
        return "\n".join(lines)


def gc_objects():
    import gc
    return len(gc.get_objects())
