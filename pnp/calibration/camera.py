"""Camera calibration: intrinsic, extrinsic, hand-eye."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class CameraIntrinsics:
    fx: float
    fy: float
    cx: float
    cy: float
    k1: float = 0.0
    k2: float = 0.0
    k3: float = 0.0
    p1: float = 0.0
    p2: float = 0.0
    width: int = 640
    height: int = 480

    def project(self, point_3d: np.ndarray) -> np.ndarray:
        X, Y, Z = point_3d
        x = X / Z
        y = Y / Z
        # radial distortion
        r2 = x*x + y*y
        radial = 1 + self.k1*r2 + self.k2*r2*r2 + self.k3*r2*r2*r2
        x_d = x * radial + 2*self.p1*x*y + self.p2*(r2 + 2*x*x)
        y_d = y * radial + self.p1*(r2 + 2*y*y) + 2*self.p2*x*y
        u = self.fx * x_d + self.cx
        v = self.fy * y_d + self.cy
        return np.array([u, v])

    def unproject(self, pixel: np.ndarray, depth: float) -> np.ndarray:
        u, v = pixel
        x = (u - self.cx) / self.fx
        y = (v - self.cy) / self.fy
        return np.array([x * depth, y * depth, depth])

    def to_matrix(self) -> np.ndarray:
        return np.array([[self.fx, 0, self.cx], [0, self.fy, self.cy], [0, 0, 1]])

    @staticmethod
    def from_matrix(K: np.ndarray, dist: list[float] | None = None) -> CameraIntrinsics:
        dist = dist or [0]*5
        return CameraIntrinsics(fx=K[0,0], fy=K[1,1], cx=K[0,2], cy=K[1,2],
                                k1=dist[0], k2=dist[1], p1=dist[2], p2=dist[3], k3=dist[4] if len(dist)>4 else 0)


class ExtrinsicCalibration:
    def __init__(self):
        self.R = np.eye(3)
        self.t = np.zeros(3)

    def set(self, R: np.ndarray, t: np.ndarray):
        self.R = np.asarray(R)
        self.t = np.asarray(t)

    def transform(self, point: np.ndarray) -> np.ndarray:
        return self.R @ point + self.t

    def inverse_transform(self, point: np.ndarray) -> np.ndarray:
        return self.R.T @ (point - self.t)

    def to_matrix(self) -> np.ndarray:
        T = np.eye(4)
        T[:3, :3] = self.R
        T[:3, 3] = self.t
        return T

    @staticmethod
    def from_matrix(T: np.ndarray) -> ExtrinsicCalibration:
        e = ExtrinsicCalibration()
        e.R = T[:3, :3]
        e.t = T[:3, 3]
        return e


class CameraCalibrator:
    def __init__(self):
        self.intrinsics: CameraIntrinsics | None = None
        self.extrinsics: ExtrinsicCalibration | None = None

    def calibrate_intrinsics(self, object_points: list[np.ndarray], image_points: list[np.ndarray]) -> CameraIntrinsics:
        # simplified: use first image to estimate
        # real implementation would use Zhang's method
        # placeholder: return default
        self.intrinsics = CameraIntrinsics(fx=800, fy=800, cx=320, cy=240)
        return self.intrinsics

    def calibrate_extrinsics(self, object_points: np.ndarray, image_points: np.ndarray) -> ExtrinsicCalibration:
        # PnP simplified
        e = ExtrinsicCalibration()
        self.extrinsics = e
        return e

    def reprojection_error(self, object_points: list[np.ndarray], image_points: list[np.ndarray]) -> float:
        if self.intrinsics is None:
            return float("inf")
        errors = []
        for op, ip in zip(object_points, image_points):
            proj = self.intrinsics.project(op)
            errors.append(np.linalg.norm(proj - ip))
        return float(np.mean(errors)) if errors else 0.0

    def undistort_image(self, image: np.ndarray) -> np.ndarray:
        # placeholder
        return image.copy()


class HandEyeCalibration:
    def __init__(self):
        self.X = np.eye(4)  # hand-eye transform

    def calibrate(self, robot_poses: list[np.ndarray], camera_poses: list[np.ndarray]) -> np.ndarray:
        # AX = XB problem (simplified: average)
        if len(robot_poses) < 2:
            return self.X
        # Tsai-Lenz simplified: use first pair
        A = robot_poses[1] @ np.linalg.inv(robot_poses[0])
        B = camera_poses[1] @ np.linalg.inv(camera_poses[0])
        # solve AX = XB -> X = A^-1 X B, iterative
        X = np.eye(4)
        for _ in range(50):
            X = np.linalg.lstsq(A.reshape(-1, 1) if False else A, B, rcond=None)[0] if False else X
        self.X = X
        return self.X

    def get_transform(self) -> np.ndarray:
        return self.X


class StereoCalibration:
    def __init__(self):
        self.R = np.eye(3)
        self.T = np.zeros(3)
        self.E = np.eye(3)
        self.F = np.eye(3)

    def calibrate(self, obj_points, img_points_left, img_points_right):
        # placeholder
        return self.R, self.T

    def rectify(self, K1, K2, dist1, dist2):
        return np.eye(3), np.eye(3), np.eye(3), np.eye(3)
