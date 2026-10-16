"""Placement sequence, feeder and tray optimization algorithms."""

import numpy as np


def euclid(a, b):
    return float(np.hypot(a[0]-b[0], a[1]-b[1]))


def nearest_neighbor(points: np.ndarray, start=(0.0, 0.0)) -> list[int]:
    """Greedy nearest-neighbor ordering of 2D points."""
    pts = np.asarray(points, dtype=float)
    n = len(pts)
    remaining = list(range(n))
    order = []
    cur = np.array(start, dtype=float)
    while remaining:
        ds = np.array([np.hypot(pts[i, 0]-cur[0], pts[i, 1]-cur[1]) for i in remaining])
        j = int(np.argmin(ds))
        idx = remaining.pop(j)
        order.append(idx)
        cur = pts[idx]
    return order


def two_opt(points: np.ndarray, order: list[int], start=(0.0, 0.0)) -> list[int]:
    """2-opt improvement of a tour (open path from start)."""
    pts = np.asarray(points, dtype=float)
    order = list(order)
    n = len(order)
    if n < 4:
        return order

    def path_len(seq):
        cur = np.array(start, dtype=float)
        d = 0.0
        for idx in seq:
            d += np.hypot(pts[idx, 0]-cur[0], pts[idx, 1]-cur[1])
            cur = pts[idx]
        return d

    best = order
    best_len = path_len(best)
    improved = True
    iters = 0
    while improved and iters < 500:
        improved = False
        iters += 1
        for i in range(1, n-1):
            for j in range(i+1, n):
                cand = best[:i] + best[i:j+1][::-1] + best[j+1:]
                l = path_len(cand)
                if l < best_len - 1e-9:
                    best, best_len = cand, l
                    improved = True
    return best


def optimize_placement(targets: list[dict], start=(0.0, 0.0)) -> list[dict]:
    """Optimize placement sequence: group by component type, nearest-neighbor + 2-opt."""
    if not targets:
        return targets
    pts = np.array([(t['x'], t['z']) for t in targets], dtype=float)
    # Group by type, order groups by centroid distance from start
    types = []
    seen = set()
    for t in targets:
        if t['type'] not in seen:
            seen.add(t['type']); types.append(t['type'])
    centroids = {}
    for ty in types:
        idxs = [i for i, t in enumerate(targets) if t['type'] == ty]
        centroids[ty] = pts[idxs].mean(axis=0)
    type_order = sorted(types, key=lambda ty: np.hypot(centroids[ty][0]-start[0], centroids[ty][1]-start[1]))

    ordered_indices = []
    cur = np.array(start, dtype=float)
    for ty in type_order:
        idxs = [i for i, t in enumerate(targets) if t['type'] == ty and not targets[i].get('placed', False)]
        if not idxs:
            continue
        sub_pts = pts[idxs]
        # map local
        local_order = nearest_neighbor(sub_pts, start=(cur[0], cur[1]))
        local_order = two_opt(sub_pts, local_order, start=(cur[0], cur[1]))
        for lo in local_order:
            ordered_indices.append(idxs[lo])
        if ordered_indices:
            cur = pts[ordered_indices[-1]]
    # append any missing (placed or skipped)
    for i in range(len(targets)):
        if i not in ordered_indices:
            ordered_indices.append(i)
    return [targets[i] for i in ordered_indices]


def optimize_feeders(targets: list[dict], feeders: list[dict]) -> list[dict]:
    """Reorder feeder list by component centroid X (left-to-right demand)."""
    # compute centroid x per type
    centroid_x = {}
    count = {}
    for t in targets:
        if t.get('placed'):
            continue
        centroid_x[t['type']] = centroid_x.get(t['type'], 0.0) + t['x']
        count[t['type']] = count.get(t['type'], 0) + 1
    for ty in centroid_x:
        centroid_x[ty] /= max(count[ty], 1)
    # sort needed types by centroid x
    needed = sorted(centroid_x.keys(), key=lambda ty: centroid_x[ty])
    # preserve counts by type from feeders
    type_counts = {}
    for f in feeders:
        if f.get('type'):
            type_counts[f['type']] = type_counts.get(f['type'], 0) + f.get('count', 0)
    # build new feeder list
    new_feeders = []
    for ty in needed:
        if type_counts.get(ty, 0) > 0:
            new_feeders.append({'type': ty, 'count': type_counts[ty]})
    # append extras
    for f in feeders:
        if f.get('type') and f['type'] not in needed and f.get('count', 0) > 0:
            new_feeders.append({'type': f['type'], 'count': f['count']})
    # pad to original length with empty
    while len(new_feeders) < len(feeders):
        new_feeders.append({'type': None, 'count': 0})
    # copy back metadata from original feeders where possible
    for i, f in enumerate(new_feeders):
        if i < len(feeders):
            for k in ('id', 'width', 'maxCount', 'slot', 'cols', 'rows'):
                if k in feeders[i]:
                    f[k] = feeders[i][k]
    return new_feeders


def optimize_turntable(targets: list[dict], slots: int = 12) -> list[dict]:
    """Assign turntable slots by angular centroid of target positions."""
    cx, cz = -180.0, 80.0  # turntable center default
    ang_centroid = {}
    ang_count = {}
    for t in targets:
        if t.get('placed'):
            continue
        a = np.arctan2(t['z']-cz, t['x']-cx)
        ang_centroid[t['type']] = ang_centroid.get(t['type'], 0.0) + a
        ang_count[t['type']] = ang_count.get(t['type'], 0) + 1
    for ty in ang_centroid:
        ang_centroid[ty] /= max(ang_count[ty], 1)
    needed = sorted(ang_centroid.keys(), key=lambda ty: ang_centroid[ty])
    # counts by type
    # caller passes slots as list of dicts; handle generically
    result = [{'slot': i, 'type': None, 'count': 0} for i in range(slots)]
    # if input slots provided with counts, use them
    # (this function returns slot list; counts filled by caller if needed)
    for i, ty in enumerate(needed):
        if i >= slots:
            break
        result[i]['type'] = ty
    return result
