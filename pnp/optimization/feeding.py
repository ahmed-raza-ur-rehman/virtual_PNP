"""Feeder and turntable (circular tray) order optimization."""
from __future__ import annotations

import numpy as np


def optimize_feeders(targets: list[dict], feeders: list[dict]) -> list[dict]:
    # centroid x per type
    centroid_x: dict = {}
    count: dict = {}
    for t in targets:
        if t.get("placed"):
            continue
        centroid_x[t["type"]] = centroid_x.get(t["type"], 0.0) + t["x"]
        count[t["type"]] = count.get(t["type"], 0) + 1
    for ty in centroid_x:
        centroid_x[ty] /= max(count[ty], 1)
    needed = sorted(centroid_x, key=lambda ty: centroid_x[ty])
    type_counts = {}
    for f in feeders:
        if f.get("type"):
            type_counts[f["type"]] = type_counts.get(f["type"], 0) + f.get("count", 0)
    new_feeders: list[dict] = []
    for ty in needed:
        if type_counts.get(ty, 0) > 0:
            new_feeders.append({"type": ty, "count": type_counts[ty]})
    for f in feeders:
        if f.get("type") and f["type"] not in needed and f.get("count", 0) > 0:
            new_feeders.append({"type": f["type"], "count": f["count"]})
    while len(new_feeders) < len(feeders):
        new_feeders.append({"type": None, "count": 0})
    # preserve metadata
    for i, f in enumerate(new_feeders):
        if i < len(feeders):
            for k in ("id", "width", "maxCount", "slot", "cols", "rows"):
                if k in feeders[i]:
                    f[k] = feeders[i][k]
    return new_feeders


def optimize_turntable(targets: list[dict], slots: int = 12, center=(-180.0, 80.0)) -> list[dict]:
    cx, cz = center
    ang_centroid: dict = {}
    ang_count: dict = {}
    for t in targets:
        if t.get("placed"):
            continue
        a = float(np.arctan2(t["z"] - cz, t["x"] - cx))
        ang_centroid[t["type"]] = ang_centroid.get(t["type"], 0.0) + a
        ang_count[t["type"]] = ang_count.get(t["type"], 0) + 1
    for ty in ang_centroid:
        ang_centroid[ty] /= max(ang_count[ty], 1)
    needed = sorted(ang_centroid, key=lambda ty: ang_centroid[ty])
    result = [{"slot": i, "type": None, "count": 0} for i in range(slots)]
    for i, ty in enumerate(needed):
        if i >= slots:
            break
        result[i]["type"] = ty
    return result
