"""Maze router with multiple passes."""
from __future__ import annotations

from collections import deque

import numpy as np


class MazeRouter:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid = np.zeros((height, width), dtype=int)  # 0 free, 1 blocked
        self.routes: list[list[tuple[int, int]]] = []

    def block(self, x: int, y: int):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y, x] = 1

    def route(self, src: tuple[int, int], dst: tuple[int, int]) -> list[tuple[int, int]]:
        """BFS maze routing."""
        if src == dst:
            return [src]
        visited = np.zeros_like(self.grid, dtype=bool)
        parent = {}
        q = deque([src])
        visited[src[1], src[0]] = True
        found = False
        while q:
            x, y = q.popleft()
            if (x, y) == dst:
                found = True
                break
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x + dx, y + dy
                if (0 <= nx < self.width and 0 <= ny < self.height and
                        not visited[ny, nx] and self.grid[ny, nx] == 0):
                        visited[ny, nx] = True
                        parent[(nx, ny)] = (x, y)
                        q.append((nx, ny))
        if not found:
            return []
        # reconstruct
        path = []
        cur = dst
        while cur != src:
            path.append(cur)
            cur = parent[cur]
        path.append(src)
        path.reverse()
        # mark as blocked
        for (x, y) in path:
            self.grid[y, x] = 1
        self.routes.append(path)
        return path

    def route_all(self, nets: list[tuple[tuple[int,int], tuple[int,int]]]) -> list[list[tuple[int,int]]]:
        results = []
        for src, dst in nets:
            r = self.route(src, dst)
            results.append(r)
        return results

    def report(self) -> str:
        return f"Grid: {self.width}x{self.height}, Routes: {len(self.routes)}, Blocked: {self.grid.sum()}"
