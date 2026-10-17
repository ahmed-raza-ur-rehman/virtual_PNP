"""Component detection in camera images."""
from __future__ import annotations

import numpy as np


def detect_components(img: np.ndarray, threshold: float = 0.5) -> list[tuple[int, int, int, int]]:
    """Detect component bounding boxes via thresholding + connected components."""
    gray = img if img.ndim == 2 else img.mean(axis=2)
    bw = gray > (gray.mean() + threshold * gray.std())
    # simple connected components via flood fill (coarse)
    boxes = []
    visited = np.zeros_like(bw, dtype=bool)
    h, w = bw.shape
    for y in range(h):
        for x in range(w):
            if bw[y, x] and not visited[y, x]:
                # flood fill
                stack = [(y, x)]
                minx, maxx, miny, maxy = x, x, y, y
                while stack:
                    cy, cx = stack.pop()
                    if cy < 0 or cy >= h or cx < 0 or cx >= w:
                        continue
                    if visited[cy, cx] or not bw[cy, cx]:
                        continue
                    visited[cy, cx] = True
                    minx = min(minx, cx); maxx = max(maxx, cx)
                    miny = min(miny, cy); maxy = max(maxy, cy)
                    for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
                        stack.append((cy+dy, cx+dx))
                if (maxx - minx) > 2 and (maxy - miny) > 2:
                    boxes.append((minx, miny, maxx - minx, maxy - miny))
    return boxes


def compute_centroid(box: tuple[int, int, int, int]) -> tuple[float, float]:
    x, y, w, h = box
    return (x + w / 2.0, y + h / 2.0)
