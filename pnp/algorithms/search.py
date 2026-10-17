"""Search algorithms."""
from __future__ import annotations

import random
from collections.abc import Callable
from typing import Any


def binary_search(arr: list, target) -> int:
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def ternary_search(f: Callable, lo: float, hi: float, eps: float = 1e-9) -> float:
    while hi - lo > eps:
        m1 = lo + (hi - lo) / 3
        m2 = hi - (hi - lo) / 3
        if f(m1) < f(m2):
            hi = m2
        else:
            lo = m1
    return (lo + hi) / 2


def golden_section_search(f: Callable, a: float, b: float, tol: float = 1e-9) -> float:
    phi = (1 + 5**0.5) / 2
    c = b - (b - a) / phi
    d = a + (b - a) / phi
    while abs(b - a) > tol:
        if f(c) < f(d):
            b = d
        else:
            a = c
        c = b - (b - a) / phi
        d = a + (b - a) / phi
    return (a + b) / 2


def hill_climbing(f: Callable, x0: Any, neighbor: Callable, max_iters: int = 1000) -> Any:
    x = x0
    cur = f(x)
    for _ in range(max_iters):
        xn = neighbor(x)
        cn = f(xn)
        if cn > cur:
            x = xn
            cur = cn
        else:
            break
    return x


def simulated_annealing_search(f: Callable, x0: Any, neighbor: Callable, T0: float = 100.0, alpha: float = 0.99, max_iters: int = 10000) -> Any:
    x = x0
    cur = f(x)
    best = x
    best_val = cur
    T = T0
    for _ in range(max_iters):
        xn = neighbor(x)
        cn = f(xn)
        delta = cn - cur
        if delta > 0 or random.random() < __import__("math").exp(delta / max(T, 1e-9)):
            x = xn
            cur = cn
            if cn > best_val:
                best = xn
                best_val = cn
        T *= alpha
    return best


def beam_search(successors: Callable, heuristic: Callable, start: Any, goal: Any, beam_width: int = 5, max_depth: int = 100) -> list[Any]:
    # state: (score, path)
    beam = [(heuristic(start), [start])]
    for _ in range(max_depth):
        candidates = []
        for score, path in beam:
            state = path[-1]
            if state == goal:
                return path
            for succ in successors(state):
                if succ in path:
                    continue
                new_path = path + [succ]
                candidates.append((heuristic(succ), new_path))
        if not candidates:
            break
        candidates.sort(key=lambda x: x[0], reverse=True)
        beam = candidates[:beam_width]
    # check goal
    for score, path in beam:
        if path[-1] == goal:
            return path
    return beam[0][1] if beam else []


def ida_star(successors: Callable, heuristic: Callable, start: Any, goal: Any, max_depth: int = 100) -> list[Any]:
    threshold = heuristic(start)
    path = [start]
    visited = {start}
    while threshold < float("inf"):
        t = _search(path, 0, threshold, successors, heuristic, goal, visited)
        if t == "FOUND":
            return list(path)
        if t == float("inf"):
            return []
        threshold = t
    return []


def _search(path, g, threshold, successors, heuristic, goal, visited):
    node = path[-1]
    f = g + heuristic(node)
    if f > threshold:
        return f
    if node == goal:
        return "FOUND"
    min_exceed = float("inf")
    for succ in successors(node):
        if succ in visited:
            continue
        visited.add(succ)
        path.append(succ)
        t = _search(path, g + 1, threshold, successors, heuristic, goal, visited)
        if t == "FOUND":
            return "FOUND"
        min_exceed = min(min_exceed, t)
        path.pop()
        visited.discard(succ)
    return min_exceed


def minimax(state: Any, depth: int, maximizing: bool, evaluate: Callable, successors: Callable, alpha: float = float("-inf"), beta: float = float("inf")) -> float:
    if depth == 0:
        return evaluate(state)
    if maximizing:
        value = float("-inf")
        for succ in successors(state):
            value = max(value, minimax(succ, depth-1, False, evaluate, successors, alpha, beta))
            alpha = max(alpha, value)
            if beta <= alpha:
                break
        return value
    else:
        value = float("inf")
        for succ in successors(state):
            value = min(value, minimax(succ, depth-1, True, evaluate, successors, alpha, beta))
            beta = min(beta, value)
            if beta <= alpha:
                break
        return value


def mcts(state: Any, iterations: int, successors: Callable, evaluate: Callable, is_terminal: Callable) -> Any:
    # simplified MCTS
    root = {"state": state, "visits": 0, "value": 0.0, "children": []}
    for _ in range(iterations):
        node = root
        # selection
        while node["children"] and not is_terminal(node["state"]):
            # UCB1
            best = None; best_ucb = float("-inf")
            for c in node["children"]:
                if c["visits"] == 0:
                    ucb = float("inf")
                else:
                    ucb = c["value"]/c["visits"] + (2 * __import__("math").log(node["visits"]+1) / c["visits"])**0.5
                if ucb > best_ucb:
                    best_ucb = ucb; best = c
            node = best
        # expansion
        if not is_terminal(node["state"]) and node["visits"] > 0:
            succs = successors(node["state"])
            for s in succs:
                node["children"].append({"state": s, "visits": 0, "value": 0.0, "children": []})
            if node["children"]:
                node = node["children"][0]
        # simulation
        cur = node["state"]
        depth = 0
        while not is_terminal(cur) and depth < 50:
            succs = successors(cur)
            if not succs:
                break
            cur = random.choice(succs)
            depth += 1
        val = evaluate(cur)
        # backprop
        n = node
        while n is not None:
            n["visits"] += 1
            n["value"] += val
            # find parent (simplified: not tracked; just update root path via re-traversal not done)
            break
    # choose best child
    if root["children"]:
        best = max(root["children"], key=lambda c: c["visits"])
        return best["state"]
    return state
