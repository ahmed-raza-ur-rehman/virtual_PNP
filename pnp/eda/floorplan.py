"""Floorplanning: slicing trees, area optimization, aspect ratio."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Block:
    name: str
    width: float
    height: float
    x: float = 0.0
    y: float = 0.0
    fixed: bool = False
    pins: list[tuple[str, float, float]] = field(default_factory=list)


class Floorplanner:
    def __init__(self, outline_w: float, outline_h: float):
        self.outline_w = outline_w
        self.outline_h = outline_h
        self.blocks: list[Block] = []
        self.connections: list[tuple[str, str, float]] = []

    def add_block(self, block: Block):
        self.blocks.append(block)

    def add_connection(self, a: str, b: str, weight: float = 1.0):
        self.connections.append((a, b, weight))

    def area(self) -> float:
        if not self.blocks:
            return 0.0
        xs = [b.x + b.width for b in self.blocks]
        ys = [b.y + b.height for b in self.blocks]
        return max(xs) * max(ys) if xs and ys else 0.0

    def wirelength(self) -> float:
        wl = 0.0
        pos = {b.name: (b.x + b.width / 2, b.y + b.height / 2) for b in self.blocks}
        for a, b, w in self.connections:
            if a in pos and b in pos:
                wl += w * (abs(pos[a][0] - pos[b][0]) + abs(pos[a][1] - pos[b][1]))
        return wl

    def cost(self, alpha: float = 0.5) -> float:
        a = self.area()
        target = self.outline_w * self.outline_h
        area_pen = abs(a - target) / max(target, 1e-9)
        return alpha * area_pen + (1 - alpha) * self.wirelength() / 1e3

    def random_place(self):
        for b in self.blocks:
            if not b.fixed:
                b.x = random.uniform(0, max(1, self.outline_w - b.width))
                b.y = random.uniform(0, max(1, self.outline_h - b.height))

    def simulated_annealing(self, iterations: int = 5000, T0: float = 10.0, alpha: float = 0.995):
        self.random_place()
        best = [(b.x, b.y) for b in self.blocks]
        best_cost = self.cost()
        T = T0
        for _ in range(iterations):
            # random move
            movable = [b for b in self.blocks if not b.fixed]
            if not movable:
                break
            b = random.choice(movable)
            old = (b.x, b.y)
            b.x = random.uniform(0, max(1, self.outline_w - b.width))
            b.y = random.uniform(0, max(1, self.outline_h - b.height))
            new_cost = self.cost()
            delta = new_cost - best_cost
            if delta < 0 or random.random() < math.exp(-delta / max(T, 1e-9)):
                if new_cost < best_cost:
                    best = [(blk.x, blk.y) for blk in self.blocks]
                    best_cost = new_cost
            else:
                b.x, b.y = old
            T *= alpha
        for blk, (x, y) in zip(self.blocks, best):
            blk.x, blk.y = x, y
        return best_cost

    def check_overlap(self) -> list[tuple[str, str]]:
        overlaps = []
        for i in range(len(self.blocks)):
            for j in range(i + 1, len(self.blocks)):
                a, b = self.blocks[i], self.blocks[j]
                if (a.x < b.x + b.width and a.x + a.width > b.x and
                        a.y < b.y + b.height and a.y + a.height > b.y):
                    overlaps.append((a.name, b.name))
        return overlaps

    def aspect_ratio(self, block: Block) -> float:
        return block.width / max(block.height, 1e-9)

    def normalize(self, block: Block, target_ar: float = 1.0):
        area = block.width * block.height
        block.width = math.sqrt(area * target_ar)
        block.height = math.sqrt(area / target_ar)

    def report(self) -> str:
        lines = [f"Floorplan: outline {self.outline_w}x{self.outline_h}"]
        lines.append(f"  Blocks: {len(self.blocks)}")
        lines.append(f"  Area used: {self.area():.1f} / {self.outline_w*self.outline_h:.1f}")
        lines.append(f"  Wirelength: {self.wirelength():.1f}")
        lines.append(f"  Overlaps: {len(self.check_overlap())}")
        for b in self.blocks:
            lines.append(f"    {b.name}: ({b.x:.1f},{b.y:.1f}) {b.width:.1f}x{b.height:.1f}")
        return "\n".join(lines)


class SlicingTree:
    """Binary slicing tree for floorplan."""
    def __init__(self, blocks: list[str]):
        self.blocks = list(blocks)
        self.tree: dict[str, Any] = {}

    def build_horizontal(self, left: list[str], right: list[str]):
        self.tree = {"op": "H", "left": left, "right": right}

    def build_vertical(self, left: list[str], right: list[str]):
        self.tree = {"op": "V", "left": left, "right": right}

    def evaluate(self, sizes: dict[str, tuple[float, float]]) -> tuple[float, float]:
        # returns (width, height) of root
        def rec(node):
            if isinstance(node, str):
                return sizes.get(node, (1.0, 1.0))
            if isinstance(node, list):
                # stack horizontally
                w = 0.0; h = 0.0
                for n in node:
                    nw, nh = rec(n)
                    w += nw; h = max(h, nh)
                return (w, h)
            if isinstance(node, dict):
                op = node.get("op")
                left = rec(node["left"])
                right = rec(node["right"])
                if op == "H":
                    return (max(left[0], right[0]), left[1] + right[1])
                else:
                    return (left[0] + right[0], max(left[1], right[1]))
            return (1.0, 1.0)
        return rec(self.tree) if self.tree else (0.0, 0.0)

    def area(self, sizes):
        w, h = self.evaluate(sizes)
        return w * h
