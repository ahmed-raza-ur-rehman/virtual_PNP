"""Image segmentation: thresholding, region growing, watershed, clustering."""
from __future__ import annotations

import math

import numpy as np


class Thresholding:
    @staticmethod
    def otsu(image: np.ndarray) -> int:
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(np.uint8)
        hist, _ = np.histogram(image.flatten(), bins=256, range=(0, 256))
        total = image.size
        sum_total = np.dot(np.arange(256), hist)
        sum_b = 0.0
        w_b = 0.0
        max_var = 0.0
        threshold = 0
        for t in range(256):
            w_b += hist[t]
            if w_b == 0:
                continue
            w_f = total - w_b
            if w_f == 0:
                break
            sum_b += t * hist[t]
            m_b = sum_b / w_b
            m_f = (sum_total - sum_b) / w_f
            var_between = w_b * w_f * (m_b - m_f) ** 2
            if var_between > max_var:
                max_var = var_between
                threshold = t
        return threshold

    @staticmethod
    def adaptive(image: np.ndarray, block_size: int = 11, C: int = 2) -> np.ndarray:
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(float)
        h, w = image.shape
        out = np.zeros_like(image, dtype=np.uint8)
        half = block_size // 2
        for y in range(h):
            for x in range(w):
                y0 = max(0, y - half); y1 = min(h, y + half + 1)
                x0 = max(0, x - half); x1 = min(w, x + half + 1)
                local_mean = image[y0:y1, x0:x1].mean()
                out[y, x] = 255 if image[y, x] > local_mean - C else 0
        return out

    @staticmethod
    def global_threshold(image: np.ndarray, t: int) -> np.ndarray:
        if image.ndim == 3:
            image = image.mean(axis=2)
        return (image > t).astype(np.uint8) * 255


class RegionGrowing:
    def __init__(self, threshold: float = 10.0):
        self.threshold = threshold

    def grow(self, image: np.ndarray, seed: tuple[int, int]) -> np.ndarray:
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(float)
        h, w = image.shape
        mask = np.zeros((h, w), dtype=bool)
        sy, sx = seed
        seed_val = image[sy, sx]
        stack = [(sy, sx)]
        mask[sy, sx] = True
        while stack:
            y, x = stack.pop()
            for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and not mask[ny, nx] and abs(image[ny, nx] - seed_val) <= self.threshold:
                    mask[ny, nx] = True
                    stack.append((ny, nx))
        return mask


class Watershed:
    def __init__(self):
        pass

    def segment(self, image: np.ndarray) -> np.ndarray:
        # simplified: distance transform + threshold
        if image.ndim == 3:
            image = image.mean(axis=2)
        binary = image > Thresholding.otsu(image)
        # distance transform (approx)
        from scipy import ndimage
        dist = ndimage.distance_transform_edt(binary)
        # markers: local maxima
        from scipy.ndimage import maximum_filter
        local_max = (dist == maximum_filter(dist, size=5)) & (dist > 0)
        markers = np.zeros_like(image, dtype=int)
        markers[local_max] = np.arange(1, local_max.sum() + 1)
        # simple watershed via flooding
        labels = markers.copy()
        # grow regions by distance
        changed = True
        iters = 0
        while changed and iters < 100:
            changed = False
            iters += 1
            for y in range(1, image.shape[0]-1):
                for x in range(1, image.shape[1]-1):
                    if labels[y, x] == 0 and binary[y, x]:
                        nbrs = [labels[y-1,x], labels[y+1,x], labels[y,x-1], labels[y,x+1]]
                        nonzero = [n for n in nbrs if n > 0]
                        if nonzero:
                            labels[y, x] = max(set(nonzero), key=nonzero.count)
                            changed = True
        return labels


class KMeansSegmentation:
    def __init__(self, k: int = 3, max_iters: int = 50):
        self.k = k
        self.max_iters = max_iters

    def segment(self, image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            image = np.stack([image]*3, axis=2)
        h, w, c = image.shape
        pixels = image.reshape(-1, c).astype(float)
        # init centroids
        rng = np.random.default_rng(0)
        idx = rng.choice(len(pixels), self.k, replace=False)
        centroids = pixels[idx].copy()
        labels = np.zeros(len(pixels), dtype=int)
        for _ in range(self.max_iters):
            # assign
            dists = np.linalg.norm(pixels[:, None, :] - centroids[None, :, :], axis=2)
            new_labels = np.argmin(dists, axis=1)
            if np.array_equal(new_labels, labels):
                break
            labels = new_labels
            for k in range(self.k):
                if np.any(labels == k):
                    centroids[k] = pixels[labels == k].mean(axis=0)
        return labels.reshape(h, w)


class SLIC:
    """Simple Linear Iterative Clustering (superpixels)."""
    def __init__(self, num_segments: int = 100, compactness: float = 10.0, max_iters: int = 10):
        self.num_segments = num_segments
        self.compactness = compactness
        self.max_iters = max_iters

    def segment(self, image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            image = np.stack([image]*3, axis=2)
        h, w, _c = image.shape
        # grid of centers
        S = int(math.sqrt(h * w / self.num_segments))
        centers = []
        for y in range(S // 2, h, S):
            for x in range(S // 2, w, S):
                centers.append((y, x))
        labels = -np.ones((h, w), dtype=int)
        # assign each pixel to nearest center
        for ci, (cy, cx) in enumerate(centers):
            y0 = max(0, cy - S); y1 = min(h, cy + S)
            x0 = max(0, cx - S); x1 = min(w, cx + S)
            for y in range(y0, y1):
                for x in range(x0, x1):
                    if labels[y, x] == -1:
                        labels[y, x] = ci
        # fill unassigned
        labels[labels == -1] = 0
        return labels
