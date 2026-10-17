"""Clock tree synthesis (CTS)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class ClockSink:
    name: str
    x: float
    y: float
    capacitance: float = 1e-15
    skew_tolerance: float = 0.05


@dataclass
class ClockBuffer:
    name: str
    delay: float = 0.05
    fanout: int = 4
    capacitance: float = 2e-15
    power: float = 1e-6


class ClockTreeSynthesizer:
    def __init__(self, root: tuple[float, float] = (0.0, 0.0)):
        self.root = root
        self.sinks: list[ClockSink] = []
        self.buffers: list[ClockBuffer] = []
        self.tree: dict[str, Any] = {}
        self.skew: float = 0.0
        self.latency: float = 0.0

    def add_sink(self, sink: ClockSink):
        self.sinks.append(sink)

    def add_buffer(self, buf: ClockBuffer):
        self.buffers.append(buf)

    def build_h_tree(self) -> dict[str, Any]:
        if not self.sinks:
            return {}
        xs = [s.x for s in self.sinks]
        ys = [s.y for s in self.sinks]
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        self.tree = {"type": "H", "center": (cx, cy), "sinks": [s.name for s in self.sinks]}
        return self.tree

    def build_x_tree(self) -> dict[str, Any]:
        self.tree = {"type": "X", "root": self.root, "sinks": [s.name for s in self.sinks]}
        return self.tree

    def compute_skew(self) -> float:
        if not self.sinks:
            return 0.0
        # estimate delay to each sink = manhattan distance * wire delay + buffer delays
        delays = []
        for s in self.sinks:
            dist = abs(s.x - self.root[0]) + abs(s.y - self.root[1])
            wire_delay = dist * 1e-3  # ns per unit
            buf_delay = sum(b.delay for b in self.buffers) / max(len(self.buffers), 1)
            delays.append(wire_delay + buf_delay)
        self.skew = max(delays) - min(delays) if delays else 0.0
        self.latency = max(delays) if delays else 0.0
        return self.skew

    def buffer_insertion(self, max_fanout: int = 4) -> int:
        n_bufs = 0
        # insert buffers to balance fanout
        remaining = list(self.sinks)
        while len(remaining) > max_fanout:
            # cluster nearest sinks
            clusters = []
            used = set()
            for s in remaining:
                if s.name in used:
                    continue
                cluster = [s]
                used.add(s.name)
                for s2 in remaining:
                    if s2.name in used:
                        continue
                    if len(cluster) < max_fanout:
                        dist = math.hypot(s.x - s2.x, s.y - s2.y)
                        if dist < 50:
                            cluster.append(s2)
                            used.add(s2.name)
                clusters.append(cluster)
            remaining = [ClockSink(name=f"buf_{i}", x=sum(c.x for c in cl)/len(cl), y=sum(c.y for c in cl)/len(cl)) for i, cl in enumerate(clusters)]
            n_bufs += len(clusters)
        return n_bufs

    def useful_skew(self, setup_slack: float, hold_slack: float) -> float:
        # positive useful skew helps setup, negative helps hold
        if setup_slack < 0 and hold_slack > 0:
            return min(-setup_slack, hold_slack)
        if hold_slack < 0 and setup_slack > 0:
            return -min(-hold_slack, setup_slack)
        return 0.0

    def report(self) -> str:
        self.compute_skew()
        lines = ["Clock Tree Synthesis Report"]
        lines.append(f"  Root: {self.root}")
        lines.append(f"  Sinks: {len(self.sinks)}")
        lines.append(f"  Buffers: {len(self.buffers)}")
        lines.append(f"  Skew: {self.skew:.4f} ns")
        lines.append(f"  Latency: {self.latency:.4f} ns")
        lines.append(f"  Tree type: {self.tree.get('type', 'none')}")
        return "\n".join(lines)
