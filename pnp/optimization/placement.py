"""Placement sequence optimization: TSP (nearest-neighbor + 2-opt + LKH-style)."""

from __future__ import annotations

import numpy as np
from scipy.spatial.distance import cdist


def nearest_neighbor_tour(pts: np.ndarray, start_idx: int = 0) -> list[int]:
    n = len(pts)
    unvisited = set(range(n))
    tour = [start_idx]
    unvisited.discard(start_idx)
    cur = start_idx
    while unvisited:
        ds = cdist(pts[[cur]], pts[list(unvisited)])[0]
        nxt = list(unvisited)[int(np.argmin(ds))]
        tour.append(nxt)
        unvisited.discard(nxt)
        cur = nxt
    return tour


def two_opt_tour(pts: np.ndarray, tour: list[int]) -> list[int]:
    tour = list(tour)
    n = len(tour)
    improved = True
    it = 0
    while improved and it < 1000:
        improved = False
        it += 1
        for i in range(1, n - 2):
            for j in range(i + 1, n):
                if j - i == 1:
                    continue
                a, b = tour[i - 1], tour[i]
                c, d = tour[j - 1], tour[(j) % n]
                cur = np.linalg.norm(pts[a] - pts[b]) + np.linalg.norm(pts[c] - pts[d])
                new = np.linalg.norm(pts[a] - pts[c]) + np.linalg.norm(pts[b] - pts[d])
                if new < cur - 1e-12:
                    tour[i:j] = tour[i:j][::-1]
                    improved = True
    return tour


def optimize_placement(targets: list[dict], start=(0.0, 0.0)) -> list[dict]:
    if not targets:
        return targets
    unplaced = [t for t in targets if not t.get("placed", False)]
    placed = [t for t in targets if t.get("placed", False)]
    if not unplaced:
        return targets
    pts = np.array([(t["x"], t["z"]) for t in unplaced], dtype=float)
    start_pt = np.array(start, dtype=float)
    # prepend virtual start
    np.vstack([start_pt[None, :], pts])
    # group by type: optimize each type block
    types = []
    seen = set()
    for t in unplaced:
        if t["type"] not in seen:
            seen.add(t["type"])
            types.append(t["type"])
    centroids = {
        ty: pts[[i for i, t in enumerate(unplaced) if t["type"] == ty]].mean(axis=0) for ty in types
    }
    type_order = sorted(types, key=lambda ty: np.linalg.norm(centroids[ty] - start_pt))
    ordered_local = []
    cur = start_pt
    for ty in type_order:
        idxs = [i for i, t in enumerate(unplaced) if t["type"] == ty]
        if not idxs:
            continue
        sub = pts[idxs]
        # nearest neighbor within type starting from cur
        rem = list(range(len(idxs)))
        seq = []
        c = cur
        while rem:
            ds = np.array([np.linalg.norm(sub[r] - c) for r in rem])
            j = int(np.argmin(ds))
            seq.append(rem.pop(j))
            c = sub[seq[-1]]
        # map back to unplaced indices
        for lo in seq:
            ordered_local.append(idxs[lo])
        if ordered_local:
            cur = pts[ordered_local[-1]]
    # 2-opt on full ordered set
    pts[ordered_local] if ordered_local else pts
    # build tour indices into ordered_local then refine positions
    list(range(len(ordered_local)))
    # refine using 2-opt on actual points
    pts[ordered_local]

    # nearest neighbor baseline already; apply 2-opt on index list
    # (operate on ordered_local directly)
    def path_len(seq):
        c = start_pt
        d = 0.0
        for i in seq:
            d += np.linalg.norm(pts[i] - c)
            c = pts[i]
        return d

    # 2-opt (incremental delta)
    seq = list(ordered_local)
    nseq = len(seq)
    def dd(a, b):
        return float(np.linalg.norm(pts[a] - pts[b]))
    improved = True
    it = 0
    while improved and it < 5:
        improved = False
        it += 1
        for i in range(1, nseq - 1):
            for j in range(i + 1, nseq):
                if j + 1 >= nseq:
                    continue
                a, b = seq[i-1], seq[i]
                c, d2 = seq[j], seq[j+1]
                old = dd(a, b) + dd(c, d2)
                new = dd(a, c) + dd(b, d2)
                if new < old - 1e-12:
                    seq[i:j+1] = seq[i:j+1][::-1]
                    improved = True
    # append any missing
    for i in range(len(unplaced)):
        if i not in [unplaced.index(u) for u in unplaced if False] and i not in []:
            pass
    present = set(seq)
    for i in range(len(unplaced)):
        if i not in present:
            seq.append(i)
    new_unplaced = [unplaced[i] for i in seq]
    return placed + new_unplaced
