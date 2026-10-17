"""Graph algorithms for path planning and optimization."""
from __future__ import annotations

import heapq
from collections import deque
from collections.abc import Callable
from typing import Any


class Graph:
    def __init__(self, directed: bool = False):
        self.adj: dict[Any, list[tuple[Any, float]]] = {}
        self.directed = directed
        self.nodes: set[Any] = set()

    def add_node(self, n):
        self.nodes.add(n)
        self.adj.setdefault(n, [])

    def add_edge(self, u, v, w: float = 1.0):
        self.add_node(u); self.add_node(v)
        self.adj[u].append((v, w))
        if not self.directed:
            self.adj[v].append((u, w))

    def neighbors(self, n):
        return self.adj.get(n, [])

    def dijkstra(self, src, dst=None) -> dict[Any, float]:
        dist = {n: float("inf") for n in self.nodes}
        dist[src] = 0
        pq = [(0, src)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            if dst is not None and u == dst:
                break
            for v, w in self.neighbors(u):
                nd = d + w
                if nd < dist.get(v, float("inf")):
                    dist[v] = nd
                    heapq.heappush(pq, (nd, v))
        return dist

    def shortest_path(self, src, dst) -> list[Any]:
        dist = {n: float("inf") for n in self.nodes}
        prev = {n: None for n in self.nodes}
        dist[src] = 0
        pq = [(0, src)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == dst:
                break
            if d > dist[u]:
                continue
            for v, w in self.neighbors(u):
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
        # reconstruct
        path = []
        cur = dst
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        if path and path[0] != src:
            return []
        return path

    def astar(self, src, dst, heuristic: Callable[[Any, Any], float]) -> list[Any]:
        g = {n: float("inf") for n in self.nodes}
        f = {n: float("inf") for n in self.nodes}
        g[src] = 0
        f[src] = heuristic(src, dst)
        pq = [(f[src], src)]
        prev = {n: None for n in self.nodes}
        closed = set()
        while pq:
            _, u = heapq.heappop(pq)
            if u == dst:
                break
            if u in closed:
                continue
            closed.add(u)
            for v, w in self.neighbors(u):
                if v in closed:
                    continue
                tg = g[u] + w
                if tg < g[v]:
                    prev[v] = u
                    g[v] = tg
                    f[v] = tg + heuristic(v, dst)
                    heapq.heappush(pq, (f[v], v))
        path = []
        cur = dst
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        if not path or path[0] != src:
            return []
        return path

    def bellman_ford(self, src) -> tuple[dict, bool]:
        dist = {n: float("inf") for n in self.nodes}
        dist[src] = 0
        for _ in range(len(self.nodes) - 1):
            updated = False
            for u in self.nodes:
                for v, w in self.neighbors(u):
                    if dist[u] + w < dist[v]:
                        dist[v] = dist[u] + w
                        updated = True
            if not updated:
                break
        # check negative cycle
        neg_cycle = False
        for u in self.nodes:
            for v, w in self.neighbors(u):
                if dist[u] + w < dist[v]:
                    neg_cycle = True
        return dist, neg_cycle

    def floyd_warshall(self) -> dict:
        nodes = list(self.nodes)
        idx = {n: i for i, n in enumerate(nodes)}
        n = len(nodes)
        D = [[float("inf")] * n for _ in range(n)]
        for i in range(n):
            D[i][i] = 0
        for u in self.nodes:
            for v, w in self.neighbors(u):
                D[idx[u]][idx[v]] = min(D[idx[u]][idx[v]], w)
        for k in range(n):
            for i in range(n):
                for j in range(n):
                    D[i][j] = min(D[i][j], D[i][k] + D[k][j])
        return {nodes[i]: {nodes[j]: D[i][j] for j in range(n)} for i in range(n)}

    def bfs(self, src) -> dict[Any, int]:
        dist = {src: 0}
        q = deque([src])
        while q:
            u = q.popleft()
            for v, _ in self.neighbors(u):
                if v not in dist:
                    dist[v] = dist[u] + 1
                    q.append(v)
        return dist

    def dfs(self, src, visited=None) -> list[Any]:
        if visited is None:
            visited = set()
        order = []
        stack = [src]
        while stack:
            u = stack.pop()
            if u in visited:
                continue
            visited.add(u)
            order.append(u)
            for v, _ in self.neighbors(u):
                if v not in visited:
                    stack.append(v)
        return order

    def topological_sort(self) -> list[Any]:
        indeg = {n: 0 for n in self.nodes}
        for u in self.nodes:
            for v, _ in self.neighbors(u):
                indeg[v] += 1
        q = deque([n for n in self.nodes if indeg[n] == 0])
        order = []
        while q:
            u = q.popleft()
            order.append(u)
            for v, _ in self.neighbors(u):
                indeg[v] -= 1
                if indeg[v] == 0:
                    q.append(v)
        return order

    def connected_components(self) -> list[set[Any]]:
        visited = set()
        comps = []
        for n in self.nodes:
            if n in visited:
                continue
            comp = set()
            stack = [n]
            while stack:
                u = stack.pop()
                if u in visited:
                    continue
                visited.add(u)
                comp.add(u)
                for v, _ in self.neighbors(u):
                    if v not in visited:
                        stack.append(v)
            comps.append(comp)
        return comps

    def minimum_spanning_tree(self) -> list[tuple[Any, Any, float]]:
        if not self.nodes:
            return []
        edges = []
        for u in self.nodes:
            for v, w in self.neighbors(u):
                edges.append((w, u, v))
        edges.sort()
        parent = {n: n for n in self.nodes}
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        mst = []
        for w, u, v in edges:
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[ru] = rv
                mst.append((u, v, w))
        return mst

    def max_flow(self, src, sink) -> float:
        # Edmonds-Karp
        cap = {}
        for u in self.nodes:
            for v, w in self.neighbors(u):
                cap[(u, v)] = cap.get((u, v), 0) + w
                cap.setdefault((v, u), 0)
        flow = 0
        while True:
            # BFS augmenting path
            parent = {src: None}
            q = deque([src])
            found = False
            while q:
                u = q.popleft()
                if u == sink:
                    found = True
                    break
                for v, _ in self.neighbors(u):
                    if v not in parent and cap.get((u, v), 0) > 0:
                        parent[v] = u
                        q.append(v)
                # also consider reverse edges
                for v in self.nodes:
                    if v not in parent and cap.get((u, v), 0) > 0:
                        pass
            if not found and sink not in parent:
                break
            if sink not in parent:
                break
            # find bottleneck
            path_flow = float("inf")
            v = sink
            while parent[v] is not None:
                u = parent[v]
                path_flow = min(path_flow, cap.get((u, v), 0))
                v = u
            v = sink
            while parent[v] is not None:
                u = parent[v]
                cap[(u, v)] -= path_flow
                cap[(v, u)] = cap.get((v, u), 0) + path_flow
                v = u
            flow += path_flow
        return flow
