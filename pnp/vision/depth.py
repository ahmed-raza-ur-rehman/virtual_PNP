"""Depth estimation and stereo vision."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class CameraIntrinsics:
    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int
    dist_coeffs: list[float] = None

    def __post_init__(self):
        if self.dist_coeffs is None:
            self.dist_coeffs = [0.0] * 5

    def project(self, point_3d: np.ndarray) -> np.ndarray:
        X, Y, Z = point_3d
        x = self.fx * X / Z + self.cx
        y = self.fy * Y / Z + self.cy
        return np.array([x, y])

    def unproject(self, pixel: np.ndarray, depth: float) -> np.ndarray:
        u, v = pixel
        X = (u - self.cx) * depth / self.fx
        Y = (v - self.cy) * depth / self.fy
        return np.array([X, Y, depth])


class StereoMatcher:
    def __init__(self, num_disparities: int = 64, block_size: int = 11):
        self.num_disparities = num_disparities
        self.block_size = block_size

    def compute_disparity(self, left: np.ndarray, right: np.ndarray) -> np.ndarray:
        if left.ndim == 3:
            left = left.mean(axis=2)
            right = right.mean(axis=2)
        left = left.astype(float)
        right = right.astype(float)
        h, w = left.shape
        disp = np.zeros((h, w), dtype=np.float32)
        half = self.block_size // 2
        for y in range(half, h - half):
            for x in range(self.num_disparities, w - half):
                best_d = 0
                best_cost = float("inf")
                template = left[y-half:y+half+1, x-half:x+half+1]
                for d in range(self.num_disparities):
                    xr = x - d
                    if xr - half < 0:
                        break
                    patch = right[y-half:y+half+1, xr-half:xr+half+1]
                    if patch.shape != template.shape:
                        continue
                    cost = np.sum((template - patch) ** 2)
                    if cost < best_cost:
                        best_cost = cost
                        best_d = d
                disp[y, x] = best_d
        return disp

    def disparity_to_depth(self, disp: np.ndarray, focal: float, baseline: float) -> np.ndarray:
        depth = np.zeros_like(disp, dtype=float)
        mask = disp > 0
        depth[mask] = focal * baseline / disp[mask]
        return depth


class DepthFilter:
    @staticmethod
    def bilateral(depth: np.ndarray, sigma_color: float = 10.0, sigma_space: float = 5.0) -> np.ndarray:
        # simplified: gaussian blur
        from scipy.ndimage import gaussian_filter
        return gaussian_filter(depth, sigma=sigma_space)

    @staticmethod
    def median(depth: np.ndarray, size: int = 3) -> np.ndarray:
        from scipy.ndimage import median_filter
        return median_filter(depth, size=size)

    @staticmethod
    def fill_holes(depth: np.ndarray) -> np.ndarray:
        mask = depth == 0
        from scipy.ndimage import gaussian_filter
        filled = depth.copy()
        # simple inpainting: blur
        blurred = gaussian_filter(np.where(mask, 0, depth), sigma=3)
        filled[mask] = blurred[mask]
        return filled


class PointCloud:
    def __init__(self, points: np.ndarray | None = None):
        self.points = points if points is not None else np.zeros((0, 3))
        self.colors = None

    def from_depth(self, depth: np.ndarray, intrinsics: CameraIntrinsics):
        h, w = depth.shape
        pts = []
        for v in range(h):
            for u in range(w):
                d = depth[v, u]
                if d <= 0:
                    continue
                p = intrinsics.unproject(np.array([u, v]), float(d))
                pts.append(p)
        self.points = np.array(pts) if pts else np.zeros((0, 3))
        return self

    def downsample(self, voxel_size: float) -> PointCloud:
        if len(self.points) == 0:
            return self
        # voxel grid
        voxels = np.floor(self.points / voxel_size).astype(int)
        _unique, idx = np.unique(voxels, axis=0, return_index=True)
        self.points = self.points[idx]
        return self

    def transform(self, matrix: np.ndarray) -> PointCloud:
        if len(self.points) == 0:
            return self
        hom = np.hstack([self.points, np.ones((len(self.points), 1))])
        self.points = (matrix @ hom.T).T[:, :3]
        return self

    def save_ply(self, path: str):
        with open(path, "w") as f:
            f.write("ply\nformat ascii 1.0\n")
            f.write(f"element vertex {len(self.points)}\n")
            f.write("property float x\nproperty float y\nproperty float z\n")
            f.write("end_header\n")
            f.writelines(f"{p[0]} {p[1]} {p[2]}\n" for p in self.points)

    def bounding_box(self) -> tuple[np.ndarray, np.ndarray]:
        if len(self.points) == 0:
            return np.zeros(3), np.zeros(3)
        return self.points.min(axis=0), self.points.max(axis=0)
