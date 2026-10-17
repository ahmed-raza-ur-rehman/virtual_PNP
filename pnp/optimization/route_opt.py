"""Route optimization for pick-and-place head movement."""
from __future__ import annotations

import numpy as np


def total_distance(route: list[int], points: np.ndarray) -> float:
    d = 0.0
    for i in range(len(route) - 1):
        d += np.linalg.norm(points[route[i]] - points[route[i+1]])
    if len(route) > 0:
        d += np.linalg.norm(points[route[-1]] - points[route[0]])
    return float(d)


def nearest_neighbor(points: np.ndarray, start: int = 0) -> list[int]:
    n = len(points)
    visited = [False] * n
    route = [start]
    visited[start] = True
    cur = start
    for _ in range(n - 1):
        best = -1
        best_d = float("inf")
        for j in range(n):
            if not visited[j]:
                dd = np.linalg.norm(points[cur] - points[j])
                if dd < best_d:
                    best_d = dd
                    best = j
        if best == -1:
            break
        route.append(best)
        visited[best] = True
        cur = best
    return route


def two_opt(route: list[int], points: np.ndarray, max_iters: int = 1000) -> list[int]:
    route = list(route)
    n = len(route)
    improved = True
    iters = 0
    while improved and iters < max_iters:
        improved = False
        iters += 1
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                # compute delta
                a, b = route[i-1], route[i]
                c, d = route[j], route[(j+1) % n]
                old = np.linalg.norm(points[a]-points[b]) + np.linalg.norm(points[c]-points[d])
                new = np.linalg.norm(points[a]-points[c]) + np.linalg.norm(points[b]-points[d])
                if new < old - 1e-9:
                    route[i:j+1] = route[i:j+1][::-1]
                    improved = True
    return route


def or_opt(route: list[int], points: np.ndarray, segment_length: int = 1) -> list[int]:
    route = list(route)
    n = len(route)
    improved = True
    while improved:
        improved = False
        for i in range(n):
            for j in range(n):
                if abs(i - j) <= segment_length:
                    continue
                # move segment
                seg = route[i:i+segment_length]
                rest = route[:i] + route[i+segment_length:]
                # insert at j
                if j > i:
                    j -= segment_length
                new_route = rest[:j] + seg + rest[j:]
                if total_distance(new_route, points) < total_distance(route, points) - 1e-9:
                    route = new_route
                    improved = True
                    break
            if improved:
                break
    return route


def lin_kernighan(route: list[int], points: np.ndarray, max_depth: int = 5) -> list[int]:
    # simplified LK: try 2-opt moves
    return two_opt(route, points, max_iters=100)


def christofides(points: np.ndarray) -> list[int]:
    # simplified: nearest neighbor + 2-opt
    route = nearest_neighbor(points)
    route = two_opt(route, points)
    return route


def optimize_route(points: np.ndarray, method: str = "2opt") -> list[int]:
    if method == "nn":
        return nearest_neighbor(points)
    if method == "2opt":
        route = nearest_neighbor(points)
        return two_opt(route, points)
    if method == "oropt":
        route = nearest_neighbor(points)
        return or_opt(route, points)
    if method == "christofides":
        return christofides(points)
    return nearest_neighbor(points)


class RouteOptimizer:
    def __init__(self, points: np.ndarray):
        self.points = np.asarray(points, dtype=float)
        self.best_route: list[int] = []
        self.best_distance = float("inf")

    def optimize(self, method: str = "2opt", restarts: int = 5) -> list[int]:
        for _ in range(restarts):
            # random start
            start = np.random.randint(len(self.points))
            route = nearest_neighbor(self.points, start)
            route = two_opt(route, self.points)
            d = total_distance(route, self.points)
            if d < self.best_distance:
                self.best_distance = d
                self.best_route = route
        return self.best_route

    def get_distance(self) -> float:
        return self.best_distance
