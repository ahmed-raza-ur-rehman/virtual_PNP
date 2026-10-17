"""RRT and RRT* path planning."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class RRTNode:
    position: np.ndarray
    parent: RRTNode | None = None
    cost: float = 0.0
    children: list[RRTNode] = field(default_factory=list)


class RRT:
    def __init__(self, start: np.ndarray, goal: np.ndarray, bounds: tuple, step_size: float = 0.5, max_iters: int = 5000, goal_bias: float = 0.1):
        self.start = RRTNode(position=np.asarray(start, dtype=float))
        self.goal = np.asarray(goal, dtype=float)
        self.bounds = bounds  # ((xmin,xmax),(ymin,ymax)) or 3D
        self.step_size = step_size
        self.max_iters = max_iters
        self.goal_bias = goal_bias
        self.nodes: list[RRTNode] = [self.start]
        self.goal_reached = False
        self.goal_node: RRTNode | None = None

    def plan(self, obstacles: list[Any] | None = None) -> list[np.ndarray]:
        obstacles = obstacles or []
        for it in range(self.max_iters):
            # sample
            if random.random() < self.goal_bias:
                sample = self.goal.copy()
            else:
                sample = self._random_sample()
            # nearest
            nearest = self._nearest(sample)
            # steer
            new_pos = self._steer(nearest.position, sample)
            if self._collision_free(nearest.position, new_pos, obstacles):
                new_node = RRTNode(position=new_pos, parent=nearest, cost=nearest.cost + np.linalg.norm(new_pos - nearest.position))
                nearest.children.append(new_node)
                self.nodes.append(new_node)
                # check goal
                if np.linalg.norm(new_pos - self.goal) < self.step_size:
                    self.goal_reached = True
                    self.goal_node = new_node
                    return self._extract_path(new_node)
        return []

    def _random_sample(self) -> np.ndarray:
        if len(self.bounds) == 2:
            # 2D bounds: ((xmin,xmax),(ymin,ymax))
            x = random.uniform(self.bounds[0][0], self.bounds[0][1])
            y = random.uniform(self.bounds[1][0], self.bounds[1][1])
            return np.array([x, y])
        # 3D
        x = random.uniform(self.bounds[0][0], self.bounds[0][1])
        y = random.uniform(self.bounds[1][0], self.bounds[1][1])
        z = random.uniform(self.bounds[2][0], self.bounds[2][1])
        return np.array([x, y, z])

    def _nearest(self, sample: np.ndarray) -> RRTNode:
        return min(self.nodes, key=lambda n: np.linalg.norm(n.position - sample))

    def _steer(self, from_pos: np.ndarray, to_pos: np.ndarray) -> np.ndarray:
        direction = to_pos - from_pos
        dist = np.linalg.norm(direction)
        if dist <= self.step_size:
            return to_pos.copy()
        return from_pos + (direction / dist) * self.step_size

    def _collision_free(self, a: np.ndarray, b: np.ndarray, obstacles: list) -> bool:
        # check line segment against obstacles (circles/spheres)
        for obs in obstacles:
            if isinstance(obs, tuple) and len(obs) == 3:
                center, radius = obs[0], obs[1]
                # point-to-segment distance
                # simplified: check endpoints and midpoint
                for pt in [a, b, (a+b)/2]:
                    if np.linalg.norm(pt - np.asarray(center)) < radius:
                        return False
            elif isinstance(obs, tuple) and len(obs) == 4:
                # box
                pass
        return True

    def _extract_path(self, node: RRTNode) -> list[np.ndarray]:
        path = []
        cur = node
        while cur is not None:
            path.append(cur.position.copy())
            cur = cur.parent
        path.reverse()
        # add goal
        path.append(self.goal.copy())
        return path

    def get_tree_size(self) -> int:
        return len(self.nodes)


class RRTStar(RRT):
    def __init__(self, *args, **kwargs):
        self.rewire_radius = kwargs.pop("rewire_radius", 2.0)
        super().__init__(*args, **kwargs)

    def plan(self, obstacles=None) -> list[np.ndarray]:
        obstacles = obstacles or []
        for it in range(self.max_iters):
            if random.random() < self.goal_bias:
                sample = self.goal.copy()
            else:
                sample = self._random_sample()
            nearest = self._nearest(sample)
            new_pos = self._steer(nearest.position, sample)
            if self._collision_free(nearest.position, new_pos, obstacles):
                # find near nodes
                near_nodes = [n for n in self.nodes if np.linalg.norm(n.position - new_pos) < self.rewire_radius]
                # choose parent with min cost
                best_parent = nearest
                best_cost = nearest.cost + np.linalg.norm(new_pos - nearest.position)
                for near in near_nodes:
                    cand_cost = near.cost + np.linalg.norm(new_pos - near.position)
                    if cand_cost < best_cost and self._collision_free(near.position, new_pos, obstacles):
                        best_cost = cand_cost
                        best_parent = near
                new_node = RRTNode(position=new_pos, parent=best_parent, cost=best_cost)
                best_parent.children.append(new_node)
                self.nodes.append(new_node)
                # rewire
                for near in near_nodes:
                    new_cost = new_node.cost + np.linalg.norm(near.position - new_pos)
                    if new_cost < near.cost and self._collision_free(new_pos, near.position, obstacles):
                        # remove from old parent
                        if near.parent is not None:
                            near.parent.children = [c for c in near.parent.children if c is not near]
                        near.parent = new_node
                        near.cost = new_cost
                        new_node.children.append(near)
                if np.linalg.norm(new_pos - self.goal) < self.step_size:
                    self.goal_reached = True
                    self.goal_node = new_node
                    return self._extract_path(new_node)
        return []


class PRM:
    def __init__(self, bounds, num_samples: int = 500, connection_radius: float = 2.0, step_size: float = 0.5):
        self.bounds = bounds
        self.num_samples = num_samples
        self.connection_radius = connection_radius
        self.step_size = step_size
        self.nodes: list[np.ndarray] = []
        self.graph: dict[int, list[int]] = {}
        self.obstacles: list = []

    def build_roadmap(self, obstacles: list | None = None):
        obstacles = obstacles or []
        self.obstacles = obstacles
        # sample
        self.nodes = []
        attempts = 0
        while len(self.nodes) < self.num_samples and attempts < self.num_samples * 10:
            attempts += 1
            sample = self._random_sample()
            if self._collision_free_point(sample, obstacles):
                self.nodes.append(sample)
        # connect
        n = len(self.nodes)
        self.graph = {i: [] for i in range(n)}
        for i in range(n):
            for j in range(i + 1, n):
                if np.linalg.norm(self.nodes[i] - self.nodes[j]) < self.connection_radius and self._collision_free(self.nodes[i], self.nodes[j], obstacles):
                    self.graph[i].append(j)
                    self.graph[j].append(i)

    def query(self, start: np.ndarray, goal: np.ndarray) -> list[np.ndarray]:
        # add start and goal
        start_idx = len(self.nodes)
        goal_idx = start_idx + 1
        self.nodes.append(np.asarray(start, dtype=float))
        self.nodes.append(np.asarray(goal, dtype=float))
        self.graph[start_idx] = []
        self.graph[goal_idx] = []
        # connect start
        for i in range(start_idx):
            if np.linalg.norm(self.nodes[i] - self.nodes[start_idx]) < self.connection_radius and self._collision_free(self.nodes[i], self.nodes[start_idx], self.obstacles):
                self.graph[i].append(start_idx)
                self.graph[start_idx].append(i)
        # connect goal
        for i in range(start_idx):
            if np.linalg.norm(self.nodes[i] - self.nodes[goal_idx]) < self.connection_radius and self._collision_free(self.nodes[i], self.nodes[goal_idx], self.obstacles):
                self.graph[i].append(goal_idx)
                self.graph[goal_idx].append(i)
        # Dijkstra
        import heapq
        dist = {i: float("inf") for i in range(len(self.nodes))}
        prev = {i: None for i in range(len(self.nodes))}
        dist[start_idx] = 0
        pq = [(0, start_idx)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == goal_idx:
                break
            if d > dist[u]:
                continue
            for v in self.graph.get(u, []):
                w = np.linalg.norm(self.nodes[u] - self.nodes[v])
                if d + w < dist[v]:
                    dist[v] = d + w
                    prev[v] = u
                    heapq.heappush(pq, (dist[v], v))
        # reconstruct
        path = []
        cur = goal_idx
        while cur is not None:
            path.append(self.nodes[cur])
            cur = prev[cur]
        path.reverse()
        if path and np.linalg.norm(path[0] - start) > 1e-6:
            return []
        return path

    def _random_sample(self) -> np.ndarray:
        if len(self.bounds) == 2:
            x = random.uniform(self.bounds[0][0], self.bounds[0][1])
            y = random.uniform(self.bounds[1][0], self.bounds[1][1])
            return np.array([x, y])
        x = random.uniform(self.bounds[0][0], self.bounds[0][1])
        y = random.uniform(self.bounds[1][0], self.bounds[1][1])
        z = random.uniform(self.bounds[2][0], self.bounds[2][1])
        return np.array([x, y, z])

    def _collision_free_point(self, pt, obstacles) -> bool:
        for obs in obstacles:
            if isinstance(obs, tuple) and len(obs) >= 2:
                center = np.asarray(obs[0])
                radius = obs[1]
                if np.linalg.norm(pt - center) < radius:
                    return False
        return True

    def _collision_free(self, a, b, obstacles) -> bool:
        # check intermediate points
        n = max(2, int(np.linalg.norm(a - b) / self.step_size) + 1)
        for i in range(n + 1):
            pt = a + (b - a) * (i / n)
            if not self._collision_free_point(pt, obstacles):
                return False
        return True
