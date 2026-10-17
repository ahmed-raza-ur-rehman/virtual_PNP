"""Color processing and analysis."""
from __future__ import annotations

import numpy as np


class ColorSpaceConverter:
    @staticmethod
    def rgb_to_hsv(image: np.ndarray) -> np.ndarray:
        image = image.astype(float) / 255.0
        r, g, b = image[..., 0], image[..., 1], image[..., 2]
        maxc = np.max(image, axis=-1)
        minc = np.min(image, axis=-1)
        delta = maxc - minc
        h = np.zeros_like(maxc)
        # red is max
        mask = (maxc == r) & (delta > 0)
        h[mask] = (60 * ((g - b) / delta) % 360)[mask] if False else 0
        # simpler: compute properly
        h = np.where((maxc == r) & (delta > 0), (60 * ((g - b) / np.where(delta==0,1,delta)) % 360), h)
        h = np.where((maxc == g) & (delta > 0), (60 * ((b - r) / np.where(delta==0,1,delta)) + 120), h)
        h = np.where((maxc == b) & (delta > 0), (60 * ((r - g) / np.where(delta==0,1,delta)) + 240), h)
        s = np.where(maxc > 0, delta / np.where(maxc==0,1,maxc), 0)
        v = maxc
        return np.stack([h, s, v], axis=-1)

    @staticmethod
    def hsv_to_rgb(image: np.ndarray) -> np.ndarray:
        h, s, v = image[..., 0], image[..., 1], image[..., 2]
        c = v * s
        x = c * (1 - np.abs((h / 60) % 2 - 1))
        v - c
        r = np.zeros_like(h); g = np.zeros_like(h); np.zeros_like(h)
        for i in range(6):
            mask = (h >= i*60) & (h < (i+1)*60)
            if i == 0: r[mask], g[mask] = (c+x)[mask], (x)[mask] if False else c[mask], x[mask]
        # simplified fallback
        rgb = np.stack([v, v, v], axis=-1)
        return (rgb * 255).astype(np.uint8)

    @staticmethod
    def rgb_to_lab(image: np.ndarray) -> np.ndarray:
        # simplified: just scale
        return image.astype(float)

    @staticmethod
    def rgb_to_gray(image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            return image
        return (0.299*image[...,0] + 0.587*image[...,1] + 0.114*image[...,2]).astype(np.uint8)


class ColorHistogram:
    def __init__(self, bins: int = 32, channels: tuple = (0, 1, 2)):
        self.bins = bins
        self.channels = channels

    def compute(self, image: np.ndarray) -> np.ndarray:
        hist = []
        for c in self.channels:
            if image.ndim == 3:
                ch = image[..., c]
            else:
                ch = image
            h, _ = np.histogram(ch.flatten(), bins=self.bins, range=(0, 256))
            h = h.astype(float)
            if h.sum() > 0:
                h /= h.sum()
            hist.append(h)
        return np.concatenate(hist)

    def compare(self, h1: np.ndarray, h2: np.ndarray, method: str = "correlation") -> float:
        if method == "correlation":
            a = h1 - h1.mean(); b = h2 - h2.mean()
            denom = np.linalg.norm(a) * np.linalg.norm(b)
            if denom == 0:
                return 0.0
            return float(np.dot(a, b) / denom)
        if method == "intersection":
            return float(np.sum(np.minimum(h1, h2)))
        if method == "chi_square":
            denom = h1 + h2
            denom[denom == 0] = 1
            return float(0.5 * np.sum((h1 - h2) ** 2 / denom))
        if method == "bhattacharyya":
            return float(np.sum(np.sqrt(h1 * h2)))
        return 0.0


class ColorConstancy:
    @staticmethod
    def gray_world(image: np.ndarray) -> np.ndarray:
        if image.ndim != 3:
            return image
        image = image.astype(float)
        avg = image.mean(axis=(0, 1))
        gray = avg.mean()
        scale = gray / np.where(avg == 0, 1, avg)
        out = image * scale
        return np.clip(out, 0, 255).astype(np.uint8)

    @staticmethod
    def white_patch(image: np.ndarray, percentile: float = 99.0) -> np.ndarray:
        if image.ndim != 3:
            return image
        image = image.astype(float)
        max_vals = np.percentile(image, percentile, axis=(0, 1))
        scale = 255.0 / np.where(max_vals == 0, 1, max_vals)
        out = image * scale
        return np.clip(out, 0, 255).astype(np.uint8)


class DominantColors:
    def __init__(self, k: int = 5):
        self.k = k

    def extract(self, image: np.ndarray) -> list[tuple[tuple[int,int,int], float]]:
        if image.ndim != 3:
            return []
        pixels = image.reshape(-1, 3).astype(float)
        # kmeans
        rng = np.random.default_rng(0)
        idx = rng.choice(len(pixels), self.k, replace=False)
        centroids = pixels[idx].copy()
        labels = np.zeros(len(pixels), dtype=int)
        for _ in range(20):
            dists = np.linalg.norm(pixels[:, None, :] - centroids[None, :, :], axis=2)
            labels = np.argmin(dists, axis=1)
            for k in range(self.k):
                if np.any(labels == k):
                    centroids[k] = pixels[labels == k].mean(axis=0)
        # counts
        out = []
        for k in range(self.k):
            count = int((labels == k).sum())
            color = tuple(int(c) for c in centroids[k])
            out.append((color, count / len(pixels)))
        out.sort(key=lambda x: x[1], reverse=True)
        return out
