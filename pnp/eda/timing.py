"""Static Timing Analysis (STA) engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimingArc:
    src: str
    dst: str
    delay: float
    arc_type: str = "comb"  # comb, setup, hold, recovery, removal
    slew: float = 0.0


@dataclass
class TimingPath:
    nodes: list[str] = field(default_factory=list)
    delay: float = 0.0
    slack: float = 0.0
    start: str = ""
    end: str = ""
    path_type: str = "max"  # max (setup) or min (hold)


class TimingGraph:
    """Directed graph of timing arcs for STA."""

    def __init__(self):
        self.nodes: set[str] = set()
        self.arcs: list[TimingArc] = []
        self.adj: dict[str, list[TimingArc]] = {}
        self.radj: dict[str, list[TimingArc]] = {}
        self.arrival: dict[str, float] = {}
        self.required: dict[str, float] = {}
        self.slack: dict[str, float] = {}

    def add_node(self, name: str):
        self.nodes.add(name)
        self.adj.setdefault(name, [])
        self.radj.setdefault(name, [])

    def add_arc(self, arc: TimingArc):
        self.add_node(arc.src)
        self.add_node(arc.dst)
        self.arcs.append(arc)
        self.adj[arc.src].append(arc)
        self.radj[arc.dst].append(arc)

    def topological_order(self) -> list[str]:
        indeg = {n: 0 for n in self.nodes}
        for a in self.arcs:
            indeg[a.dst] += 1
        q = [n for n in self.nodes if indeg[n] == 0]
        order = []
        while q:
            n = q.pop(0)
            order.append(n)
            for a in self.adj.get(n, []):
                indeg[a.dst] -= 1
                if indeg[a.dst] == 0:
                    q.append(a.dst)
        if len(order) != len(self.nodes):
            # cycle detected; fall back to sorted
            return sorted(self.nodes)
        return order

    def forward_propagate(self, starts: dict[str, float] | None = None):
        starts = starts or {}
        order = self.topological_order()
        for n in order:
            self.arrival[n] = starts.get(n, 0.0)
        for n in order:
            for a in self.adj.get(n, []):
                cand = self.arrival.get(n, 0.0) + a.delay
                if cand > self.arrival.get(a.dst, float("-inf")):
                    self.arrival[a.dst] = cand

    def backward_propagate(self, ends: dict[str, float] | None = None):
        ends = ends or {}
        order = list(reversed(self.topological_order()))
        for n in order:
            self.required[n] = ends.get(n, float("inf"))
        for n in order:
            for a in self.radj.get(n, []):
                cand = self.required.get(n, float("inf")) - a.delay
                if cand < self.required.get(a.src, float("inf")):
                    self.required[a.src] = cand

    def compute_slack(self):
        for n in self.nodes:
            self.slack[n] = self.required.get(n, 0.0) - self.arrival.get(n, 0.0)

    def worst_slack(self) -> float:
        if not self.slack:
            self.forward_propagate()
            self.backward_propagate()
            self.compute_slack()
        return min(self.slack.values()) if self.slack else 0.0

    def find_critical_path(self) -> TimingPath:
        self.forward_propagate()
        self.backward_propagate()
        self.compute_slack()
        # start from node with min slack among sinks
        if not self.nodes:
            return TimingPath()
        # find end node: min required-arrival? use min slack node that is sink
        sinks = [n for n in self.nodes if not self.adj.get(n)]
        if not sinks:
            sinks = list(self.nodes)
        end = min(sinks, key=lambda n: self.slack.get(n, float("inf")))
        # backtrack via arrival
        path_nodes = [end]
        cur = end
        visited = set()
        while True:
            preds = self.radj.get(cur, [])
            if not preds:
                break
            # pick predecessor maximizing arrival
            best = max(preds, key=lambda a: self.arrival.get(a.src, float("-inf")))
            if best.src in visited:
                break
            visited.add(best.src)
            path_nodes.append(best.src)
            cur = best.src
        path_nodes.reverse()
        delay = self.arrival.get(end, 0.0)
        return TimingPath(nodes=path_nodes, delay=delay, slack=self.slack.get(end, 0.0), start=path_nodes[0] if path_nodes else "", end=end)


class STAEngine:
    """Static timing analysis engine with multi-corner support."""

    def __init__(self, corners: list[str] | None = None):
        self.corners = corners or ["typical", "fast", "slow"]
        self.graphs: dict[str, TimingGraph] = {c: TimingGraph() for c in self.corners}
        self.constraints: list[dict[str, Any]] = []
        self.reports: dict[str, str] = {}

    def add_constraint(self, ctype: str, **kwargs):
        self.constraints.append({"type": ctype, **kwargs})

    def build_graph(self, netlist: dict[str, Any], corner: str = "typical"):
        g = self.graphs[corner]
        # nodes for ports and gates
        for p in netlist.get("ports", []):
            g.add_node(p)
        for gate in netlist.get("gates", []):
            out = gate.get("output")
            g.add_node(out)
            for inp in gate.get("inputs", []):
                g.add_node(inp)
                delay = self._gate_delay(gate.get("type", "BUF"), corner)
                g.add_arc(TimingArc(src=inp, dst=out, delay=delay))
        # port-to-gate connections
        for p in netlist.get("ports", []):
            for gate in netlist.get("gates", []):
                if p in gate.get("inputs", []):
                    pass

    def _gate_delay(self, gtype: str, corner: str) -> float:
        base = {"BUF": 0.05, "INV": 0.04, "NAND": 0.06, "NOR": 0.07, "DFF": 0.1, "AND": 0.06, "OR": 0.06, "XOR": 0.08}.get(gtype, 0.05)
        factor = {"typical": 1.0, "fast": 0.8, "slow": 1.3}.get(corner, 1.0)
        return base * factor

    def apply_constraints(self, corner: str = "typical"):
        g = self.graphs[corner]
        for c in self.constraints:
            if c["type"] == "clock":
                # set period on clock node
                node = c.get("node")
                period = c.get("period", 10.0)
                if node in g.nodes:
                    g.required[node] = period
            elif c["type"] == "input_delay":
                node = c.get("node")
                delay = c.get("delay", 0.0)
                if node in g.nodes:
                    g.arrival[node] = delay
            elif c["type"] == "output_delay":
                node = c.get("node")
                delay = c.get("delay", 0.0)
                if node in g.nodes:
                    g.required[node] = g.required.get(node, float("inf")) - delay

    def analyze(self, corner: str = "typical") -> dict[str, Any]:
        g = self.graphs[corner]
        self.apply_constraints(corner)
        g.forward_propagate()
        g.backward_propagate()
        g.compute_slack()
        cp = g.find_critical_path()
        wns = g.worst_slack()
        tns = sum(s for s in g.slack.values() if s < 0)
        return {
            "corner": corner,
            "wns": wns,
            "tns": tns,
            "critical_path": cp.nodes,
            "critical_delay": cp.delay,
            "num_nodes": len(g.nodes),
            "num_arcs": len(g.arcs),
            "violations": sum(1 for s in g.slack.values() if s < 0),
        }

    def analyze_all_corners(self) -> dict[str, dict[str, Any]]:
        return {c: self.analyze(c) for c in self.corners}

    def report(self, corner: str = "typical") -> str:
        r = self.analyze(corner)
        lines = [f"STA Report ({corner})", f"  WNS: {r['wns']:.3f} ns", f"  TNS: {r['tns']:.3f} ns",
                 f"  Critical path delay: {r['critical_delay']:.3f} ns", f"  Violations: {r['violations']}",
                 f"  Critical path: {' -> '.join(r['critical_path'])}"]
        return "\n".join(lines)

    def check_setup_hold(self, dff_delays: list[dict[str, float]]) -> list[dict[str, Any]]:
        results = []
        for d in dff_delays:
            setup_slack = d.get("period", 10.0) - d.get("clk_to_q", 0.1) - d.get("comb", 0.0) - d.get("setup", 0.05)
            hold_slack = d.get("comb", 0.0) + d.get("clk_to_q", 0.1) - d.get("hold", 0.02)
            results.append({"cell": d.get("cell", ""), "setup_slack": setup_slack, "hold_slack": hold_slack,
                            "setup_ok": setup_slack >= 0, "hold_ok": hold_slack >= 0})
        return results
