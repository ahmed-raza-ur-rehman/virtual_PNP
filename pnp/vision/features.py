"""Feature extraction and matching for machine vision."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class Keypoint:
    x: float
    y: float
    scale: float = 1.0
    orientation: float = 0.0
    response: float = 0.0
    descriptor: np.ndarray | None = None


class HarrisCorner:
    def __init__(self, k: float = 0.04, threshold: float = 0.01, block_size: int = 3):
        self.k = k
        self.threshold = threshold
        self.block_size = block_size

    def detect(self, image: np.ndarray) -> list[Keypoint]:
        # simplified: detect local maxima of gradient magnitude
        h, w = image.shape[:2]
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(float)
        # gradients
        gx = np.zeros_like(image)
        gy = np.zeros_like(image)
        gx[:, 1:-1] = (image[:, 2:] - image[:, :-2]) / 2
        gy[1:-1, :] = (image[2:, :] - image[:-2, :]) / 2
        # Harris response
        Ixx = gx * gx
        Iyy = gy * gy
        Ixy = gx * gy
        kps = []
        for y in range(self.block_size, h - self.block_size):
            for x in range(self.block_size, w - self.block_size):
                sxx = Ixx[y-self.block_size:y+self.block_size+1, x-self.block_size:x+self.block_size+1].sum()
                syy = Iyy[y-self.block_size:y+self.block_size+1, x-self.block_size:x+self.block_size+1].sum()
                sxy = Ixy[y-self.block_size:y+self.block_size+1, x-self.block_size:x+self.block_size+1].sum()
                det = sxx * syy - sxy * sxy
                trace = sxx + syy
                response = det - self.k * trace * trace
                if response > self.threshold * 1e6:
                    kps.append(Keypoint(x=float(x), y=float(y), response=float(response)))
        # non-maximum suppression
        return self._nms(kps, 5)

    def _nms(self, kps: list[Keypoint], radius: int) -> list[Keypoint]:
        out = []
        for kp in sorted(kps, key=lambda k: k.response, reverse=True):
            ok = True
            for o in out:
                if math.hypot(kp.x - o.x, kp.y - o.y) < radius:
                    ok = False
                    break
            if ok:
                out.append(kp)
        return out


class SIFT:
    def __init__(self, num_octaves: int = 4, scales_per_octave: int = 3):
        self.num_octaves = num_octaves
        self.scales_per_octave = scales_per_octave
        self.keypoints: list[Keypoint] = []

    def detect(self, image: np.ndarray) -> list[Keypoint]:
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(float)
        h, w = image.shape
        kps = []
        # Difference of Gaussians (simplified)
        for octave in range(self.num_octaves):
            scale = 2 ** octave
            sh, sw = h // scale, w // scale
            if sh < 8 or sw < 8:
                break
            img = image[::scale, ::scale]
            # local extrema of gradient magnitude
            for y in range(2, sh - 2):
                for x in range(2, sw - 2):
                    patch = img[y-1:y+2, x-1:x+2]
                    if (img[y, x] == patch.max() or img[y, x] == patch.min()) and abs(img[y, x]) > 10:
                        kps.append(Keypoint(x=float(x*scale), y=float(y*scale), scale=float(scale)))
        self.keypoints = kps
        return kps

    def compute_descriptors(self, image: np.ndarray, kps: list[Keypoint]) -> list[Keypoint]:
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(float)
        h, w = image.shape
        for kp in kps:
            x, y = int(kp.x), int(kp.y)
            # 128-dim descriptor (simplified: gradient histogram)
            desc = np.zeros(128, dtype=float)
            for dy in range(-8, 8):
                for dx in range(-8, 8):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h - 1 and 0 <= xx < w - 1:
                        gx = image[yy, xx+1] - image[yy, xx-1]
                        gy = image[yy+1, xx] - image[yy-1, xx]
                        mag = math.hypot(gx, gy)
                        ori = math.atan2(gy, gx)
                        bin_idx = int((ori + math.pi) / (2*math.pi) * 8) % 8
                        spatial_bin = (dy // 4 + 2) * 4 + (dx // 4 + 2)
                        if 0 <= spatial_bin < 16:
                            desc[spatial_bin * 8 + bin_idx] += mag
            norm = np.linalg.norm(desc)
            if norm > 0:
                desc /= norm
            kp.descriptor = desc
        return kps


class ORB:
    def __init__(self, num_features: int = 500):
        self.num_features = num_features
        self.keypoints: list[Keypoint] = []

    def detect(self, image: np.ndarray) -> list[Keypoint]:
        harris = HarrisCorner(threshold=0.005)
        kps = harris.detect(image)
        self.keypoints = kps[:self.num_features]
        return self.keypoints

    def compute_descriptors(self, image: np.ndarray, kps: list[Keypoint]) -> list[Keypoint]:
        if image.ndim == 3:
            image = image.mean(axis=2)
        image = image.astype(float)
        h, w = image.shape
        for kp in kps:
            x, y = int(kp.x), int(kp.y)
            desc = np.zeros(256, dtype=np.uint8)
            # BRIEF-like: compare pixel pairs
            rng = np.random.default_rng(42)
            pairs = rng.integers(-8, 8, size=(256, 4))
            for i, (dx1, dy1, dx2, dy2) in enumerate(pairs):
                x1, y1 = x + dx1, y + dy1
                x2, y2 = x + dx2, y + dy2
                if 0 <= x1 < w and 0 <= y1 < h and 0 <= x2 < w and 0 <= y2 < h and image[y1, x1] < image[y2, x2]:
                    desc[i] = 1
            kp.descriptor = desc
        return kps


class FeatureMatcher:
    def __init__(self, method: str = "bf", metric: str = "l2"):
        self.method = method
        self.metric = metric

    def match(self, desc1: np.ndarray, desc2: np.ndarray) -> list[tuple[int, int, float]]:
        matches = []
        for i, d1 in enumerate(desc1):
            best_j = -1
            best_dist = float("inf")
            second_best = float("inf")
            for j, d2 in enumerate(desc2):
                dist = self._distance(d1, d2)
                if dist < best_dist:
                    second_best = best_dist
                    best_dist = dist
                    best_j = j
                elif dist < second_best:
                    second_best = dist
            # ratio test
            if best_j >= 0 and best_dist < 0.75 * second_best:
                matches.append((i, best_j, float(best_dist)))
        return matches

    def _distance(self, a, b) -> float:
        a = np.asarray(a, dtype=float)
        b = np.asarray(b, dtype=float)
        if self.metric == "hamming":
            return float(np.sum(a != b))
        return float(np.linalg.norm(a - b))

    def knn_match(self, desc1, desc2, k: int = 2) -> list[list[tuple[int, int, float]]]:
        out = []
        for i, d1 in enumerate(desc1):
            dists = sorted([(j, self._distance(d1, d2)) for j, d2 in enumerate(desc2)], key=lambda x: x[1])
            out.append([(i, j, d) for j, d in dists[:k]])
        return out

    def ransac_homography(self, pts1: np.ndarray, pts2: np.ndarray, threshold: float = 5.0, max_iters: int = 1000) -> tuple[np.ndarray, np.ndarray]:
        best_H = np.eye(3)
        best_inliers = np.zeros(len(pts1), dtype=bool)
        if len(pts1) < 4:
            return best_H, best_inliers
        rng = np.random.default_rng(0)
        for _ in range(max_iters):
            idx = rng.choice(len(pts1), 4, replace=False)
            H = self._compute_homography(pts1[idx], pts2[idx])
            if H is None:
                continue
            # count inliers
            inliers = self._count_inliers(H, pts1, pts2, threshold)
            if inliers.sum() > best_inliers.sum():
                best_inliers = inliers
                best_H = H
        return best_H, best_inliers

    def _compute_homography(self, src, dst):
        # DLT
        A = []
        for i in range(4):
            x, y = src[i]; u, v = dst[i]
            A.append([-x, -y, -1, 0, 0, 0, u*x, u*y, u])
            A.append([0, 0, 0, -x, -y, -1, v*x, v*y, v])
        A = np.array(A)
        try:
            _, _, Vt = np.linalg.svd(A)
        except np.linalg.LinAlgError:
            return None
        H = Vt[-1].reshape(3, 3)
        if abs(H[2, 2]) < 1e-9:
            return None
        H /= H[2, 2]
        return H

    def _count_inliers(self, H, pts1, pts2, threshold):
        inliers = np.zeros(len(pts1), dtype=bool)
        for i in range(len(pts1)):
            p = np.array([pts1[i][0], pts1[i][1], 1.0])
            q = H @ p
            if abs(q[2]) < 1e-9:
                continue
            q = q[:2] / q[2]
            if np.linalg.norm(q - pts2[i]) < threshold:
                inliers[i] = True
        return inliers
