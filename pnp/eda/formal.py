"""Formal verification: model checking, equivalence checking, property checking."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Property:
    name: str
    expr: str
    kind: str = "assert"  # assert, assume, cover
    clock: str = ""
    disable_iff: str = ""


class FormalEngine:
    def __init__(self):
        self.properties: list[Property] = []
        self.state_space: dict[str, Any] = {}
        self.counterexamples: list[dict[str, Any]] = []
        self.proof_results: dict[str, str] = {}

    def add_property(self, prop: Property):
        self.properties.append(prop)

    def add_state(self, name: str, domain: list[Any]):
        self.state_space[name] = domain

    def state_count(self) -> int:
        total = 1
        for d in self.state_space.values():
            total *= len(d)
        return total

    def check_property(self, prop: Property, model: Callable[[dict], bool] | None = None) -> dict[str, Any]:
        # brute-force over state space
        if not self.state_space:
            res = {"property": prop.name, "status": "vacuous", "counterexample": None}
            self.proof_results[prop.name] = "vacuous"
            return res
        keys = list(self.state_space.keys())
        domains = [self.state_space[k] for k in keys]
        # cartesian product
        import itertools
        for combo in itertools.product(*domains):
            state = dict(zip(keys, combo))
            if model is not None:
                ok = model(state)
            else:
                ok = True
            if prop.kind == "assert" and not ok:
                self.counterexamples.append({"property": prop.name, "state": state})
                self.proof_results[prop.name] = "FAIL"
                return {"property": prop.name, "status": "FAIL", "counterexample": state}
        self.proof_results[prop.name] = "PASS"
        return {"property": prop.name, "status": "PASS", "counterexample": None}

    def check_all(self, model=None) -> dict[str, str]:
        out = {}
        for p in self.properties:
            r = self.check_property(p, model)
            out[p.name] = r["status"]
        return out

    def equivalence_check(self, spec: Callable, impl: Callable, inputs: list[dict]) -> dict[str, Any]:
        mismatches = []
        for inp in inputs:
            s = spec(inp)
            i = impl(inp)
            if s != i:
                mismatches.append({"input": inp, "spec": s, "impl": i})
        return {"equivalent": len(mismatches) == 0, "mismatches": mismatches, "num_tests": len(inputs)}

    def model_check(self, transitions: Callable[[dict], list[dict]], initial: dict, property_fn: Callable[[dict], bool], max_depth: int = 100) -> dict[str, Any]:
        # BFS over state space
        visited = set()
        queue = [(initial, 0)]
        visited.add(tuple(sorted(initial.items())))
        while queue:
            state, depth = queue.pop(0)
            if not property_fn(state):
                return {"status": "FAIL", "counterexample": state, "depth": depth}
            if depth >= max_depth:
                continue
            for ns in transitions(state):
                key = tuple(sorted(ns.items()))
                if key not in visited:
                    visited.add(key)
                    queue.append((ns, depth + 1))
        return {"status": "PASS", "states_explored": len(visited), "max_depth": max_depth}

    def report(self) -> str:
        lines = ["Formal Verification Report"]
        lines.append(f"  Properties: {len(self.properties)}")
        lines.append(f"  State space size: {self.state_count()}")
        lines.append(f"  Counterexamples: {len(self.counterexamples)}")
        for name, status in self.proof_results.items():
            lines.append(f"    {name}: {status}")
        return "\n".join(lines)


class SATSolver:
    """Simple DPLL SAT solver."""

    def __init__(self):
        self.clauses: list[list[int]] = []
        self.assignment: dict[int, bool] = {}

    def add_clause(self, clause: list[int]):
        self.clauses.append(list(clause))

    def solve(self) -> bool:
        return self._dpll(self.clauses, {})

    def _dpll(self, clauses, assignment):
        # unit propagation
        changed = True
        while changed:
            changed = False
            for c in clauses:
                unassigned = [l for l in c if abs(l) not in assignment]
                if len(unassigned) == 0:
                    # check satisfied
                    sat = any((l > 0) == assignment.get(abs(l), False) for l in c)
                    if not sat:
                        return False
                elif len(unassigned) == 1:
                    l = unassigned[0]
                    assignment[abs(l)] = l > 0
                    changed = True
        # check all satisfied
        all_sat = True
        for c in clauses:
            if not any((l > 0) == assignment.get(abs(l), False) for l in c):
                if all(abs(l) in assignment for l in c):
                    return False
                all_sat = False
        if all_sat:
            self.assignment = dict(assignment)
            return True
        # choose variable
        var = None
        for c in clauses:
            for l in c:
                if abs(l) not in assignment:
                    var = abs(l)
                    break
            if var is not None:
                break
        if var is None:
            self.assignment = dict(assignment)
            return True
        # try True
        a1 = dict(assignment); a1[var] = True
        if self._dpll(clauses, a1):
            self.assignment = a1
            return True
        # try False
        a2 = dict(assignment); a2[var] = False
        if self._dpll(clauses, a2):
            self.assignment = a2
            return True
        return False

    def get_assignment(self) -> dict[int, bool]:
        return self.assignment
