"""Placement engine with simulated annealing."""
from __future__ import annotations

import random

import numpy as np


class Placer:
    def __init__(self, width: int = 100, height: int = 100):
        self.width = width
        self.height = height
        self.cells: dict[str, tuple[int, int]] = {}
        self.cell_sizes: dict[str, tuple[int, int]] = {}

    def add_cell(self, name: str, w: int, h: int):
        self.cell_sizes[name] = (w, h)

    def place(self, netlist: dict, iterations: int = 10000, T0: float = 10.0, alpha: float = 0.99) -> dict[str, tuple[int, int]]:
        cells = list(self.cell_sizes.keys())
        # initial random placement
        for c in cells:
            self.cells[c] = (random.randint(0, self.width), random.randint(0, self.height))
        T = T0
        best = dict(self.cells)
        best_cost = self._cost(netlist)
        for it in range(iterations):
            # random move
            c = random.choice(cells)
            old_pos = self.cells[c]
            new_pos = (random.randint(0, self.width), random.randint(0, self.height))
            self.cells[c] = new_pos
            new_cost = self._cost(netlist)
            delta = new_cost - best_cost
            if delta < 0 or random.random() < np.exp(-delta / max(T, 1e-9)):
                if new_cost < best_cost:
                    best = dict(self.cells)
                    best_cost = new_cost
            else:
                self.cells[c] = old_pos
            T *= alpha
        self.cells = best
        return self.cells

    def _cost(self, netlist: dict) -> float:
        # wire length cost (Manhattan distance)
        cost = 0.0
        cells = netlist.get("cells", [])
        for i in range(len(cells)):
            for j in range(i + 1, len(cells)):
                c1 = self.cells.get(cells[i]["name"], (0, 0))
                c2 = self.cells.get(cells[j]["name"], (0, 0))
                cost += abs(c1[0] - c2[0]) + abs(c1[1] - c2[1])
        return cost

    def get_placement(self) -> dict[str, tuple[int, int]]:
        return self.cells
