"""Circuit partitioning: Fiduccia-Mattheyses, Kernighan-Lin, spectral."""
from __future__ import annotations

import random


class Partitioner:
    def __init__(self, graph: dict[str, list[str]], num_partitions: int = 2):
        self.graph = graph
        self.num_partitions = num_partitions
        self.assignment: dict[str, int] = {}
        self.cut_size: int = 0

    def random_partition(self):
        for node in self.graph:
            self.assignment[node] = random.randrange(self.num_partitions)
        self._compute_cut()

    def _compute_cut(self):
        cut = 0
        for u, neighbors in self.graph.items():
            for v in neighbors:
                if self.assignment.get(u, 0) != self.assignment.get(v, 0):
                    cut += 1
        self.cut_size = cut // 2

    def kernighan_lin(self, iterations: int = 10) -> int:
        nodes = list(self.graph.keys())
        if len(nodes) < 2:
            return 0
        # start with random balanced partition
        half = len(nodes) // 2
        self.assignment = {}
        for i, n in enumerate(nodes):
            self.assignment[n] = 0 if i < half else 1
        best_cut = None
        for _ in range(iterations):
            # compute gains
            gains = {}
            for n in nodes:
                ext = 0; int_ = 0
                for nb in self.graph.get(n, []):
                    if self.assignment[nb] != self.assignment[n]:
                        ext += 1
                    else:
                        int_ += 1
                gains[n] = ext - int_
            # swap pairs
            unlocked = set(nodes)
            swaps = []
            for _ in range(len(nodes) // 2):
                # find best unlocked node in part 0
                best0 = max((n for n in unlocked if self.assignment[n] == 0), key=lambda n: gains[n], default=None)
                best1 = max((n for n in unlocked if self.assignment[n] == 1), key=lambda n: gains[n], default=None)
                if best0 is None or best1 is None:
                    break
                swaps.append((best0, best1, gains[best0] + gains[best1]))
                # apply
                self.assignment[best0] = 1
                self.assignment[best1] = 0
                unlocked.discard(best0)
                unlocked.discard(best1)
            # find best prefix of swaps
            cum = 0; best_k = 0; best_gain = 0
            for k, (_, _, g) in enumerate(swaps, 1):
                cum += g
                if cum > best_gain:
                    best_gain = cum
                    best_k = k
            # undo all
            for a, b, _ in swaps:
                self.assignment[a] = 0
                self.assignment[b] = 1
            # apply best prefix
            for a, b, _ in swaps[:best_k]:
                self.assignment[a] = 1
                self.assignment[b] = 0
            self._compute_cut()
            if best_cut is None or self.cut_size < best_cut:
                best_cut = self.cut_size
            if best_gain <= 0:
                break
        self._compute_cut()
        return self.cut_size

    def fiduccia_mattheyses(self, iterations: int = 50) -> int:
        nodes = list(self.graph.keys())
        # initial partition
        self.random_partition()
        best_cut = self.cut_size
        best_assign = dict(self.assignment)
        for _ in range(iterations):
            # compute gains
            gain = {}
            for n in nodes:
                ext = sum(1 for nb in self.graph.get(n, []) if self.assignment[nb] != self.assignment[n])
                int_ = sum(1 for nb in self.graph.get(n, []) if self.assignment[nb] == self.assignment[n])
                gain[n] = ext - int_
            locked = set()
            moves = []
            for _ in range(len(nodes)):
                # pick highest gain unlocked node, balance partitions
                c0 = sum(1 for n in nodes if self.assignment[n] == 0 and n not in locked)
                c1 = sum(1 for n in nodes if self.assignment[n] == 1 and n not in locked)
                candidates = [n for n in nodes if n not in locked]
                if not candidates:
                    break
                # balance: prefer moving from larger partition
                if c0 > c1:
                    cand = [n for n in candidates if self.assignment[n] == 0]
                elif c1 > c0:
                    cand = [n for n in candidates if self.assignment[n] == 1]
                else:
                    cand = candidates
                if not cand:
                    cand = candidates
                n = max(cand, key=lambda x: gain[x])
                moves.append((n, gain[n]))
                # apply move
                self.assignment[n] ^= 1
                locked.add(n)
                # update gains of neighbors
                for nb in self.graph.get(n, []):
                    if nb in locked:
                        continue
                    if self.assignment[nb] == self.assignment[n]:
                        gain[nb] -= 2
                    else:
                        gain[nb] += 2
            # find best prefix
            cum = 0; best_k = 0; best_g = 0
            for k, (_, g) in enumerate(moves, 1):
                cum += g
                if cum > best_g:
                    best_g = cum
                    best_k = k
            # undo all moves
            for n, _ in moves:
                self.assignment[n] ^= 1
            # apply best prefix
            for n, _ in moves[:best_k]:
                self.assignment[n] ^= 1
            self._compute_cut()
            if self.cut_size < best_cut:
                best_cut = self.cut_size
                best_assign = dict(self.assignment)
            if best_g <= 0:
                break
        self.assignment = best_assign
        self._compute_cut()
        return self.cut_size

    def spectral_partition(self) -> int:
        # simple: use degree as proxy
        nodes = list(self.graph.keys())
        idx = {n: i for i, n in enumerate(nodes)}
        n = len(nodes)
        # build adjacency matrix
        A = [[0]*n for _ in range(n)]
        for u, nbrs in self.graph.items():
            for v in nbrs:
                A[idx[u]][idx[v]] = 1
        # degree
        deg = [sum(A[i]) for i in range(n)]
        # Fiedler vector approximation: sort by degree
        sorted(range(n), key=lambda i: deg[i])
        half = n // 2
        for i in range(n):
            self.assignment[nodes[i]] = 0 if i < half else 1
        self._compute_cut()
        return self.cut_size

    def report(self) -> str:
        self._compute_cut()
        sizes = [0] * self.num_partitions
        for v in self.assignment.values():
            sizes[v] += 1
        lines = ["Partition Report"]
        lines.append(f"  Nodes: {len(self.graph)}")
        lines.append(f"  Partitions: {self.num_partitions}")
        lines.append(f"  Cut size: {self.cut_size}")
        lines.append(f"  Partition sizes: {sizes}")
        return "\n".join(lines)
