"""Component tracking across frames."""
from __future__ import annotations

import numpy as np


def track_components(prev_boxes: list[tuple], curr_boxes: list[tuple], max_dist: float = 50.0) -> dict:
    """Match boxes between frames by nearest centroid."""
    mapping = {}
    for i, (x1, y1, w1, h1) in enumerate(prev_boxes):
        c1 = (x1 + w1/2, y1 + h1/2)
        best = None; bestd = max_dist
        for j, (x2, y2, w2, h2) in enumerate(curr_boxes):
            c2 = (x2 + w2/2, y2 + h2/2)
            d = np.hypot(c1[0]-c2[0], c1[1]-c2[1])
            if d < bestd:
                bestd = d; best = j
        if best is not None:
            mapping[i] = best
    return mapping
