"""A* path planning on a grid with obstacles."""
from __future__ import annotations
import heapq
import numpy as np
from typing import List, Tuple


def astar(grid: np.ndarray, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
    """grid: 2D array, 0 free, 1 obstacle. Returns path list."""
    h, w = grid.shape
    def heuristic(a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])
    open_set = [(heuristic(start, goal), 0, start)]
    came_from = {}
    g_score = {start: 0}
    while open_set:
        _, _, current = heapq.heappop(open_set)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nb = (current[0]+dx, current[1]+dy)
            if not (0 <= nb[0] < h and 0 <= nb[1] < w):
                continue
            if grid[nb] == 1:
                continue
            tentative = g_score[current] + 1
            if tentative < g_score.get(nb, float('inf')):
                came_from[nb] = current
                g_score[nb] = tentative
                f = tentative + heuristic(nb, goal)
                heapq.heappush(open_set, (f, tentative, nb))
    return []
