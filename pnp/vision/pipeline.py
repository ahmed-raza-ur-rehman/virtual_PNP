"""Vision pipeline: calibration, fiducial detection, alignment, orientation."""

from __future__ import annotations

import numpy as np

try:
    import cv2

    _CV2 = True
except ImportError:
    _CV2 = False


class CameraCalibration:
    def __init__(self):
        self.K = np.eye(3)
        self.dist = np.zeros(5)

    def calibrate(self, object_points, image_points, image_size):
        if _CV2:
            rms, K, dist, _rvecs, _tvecs = cv2.calibrateCamera(
                object_points, image_points, image_size, None, None
            )
            self.K, self.dist = K, dist
            return float(rms)
        return 0.0

    def undistort(self, img):
        if _CV2:
            return cv2.undistort(img, self.K, self.dist)
        return img


def detect_fiducials(img_gray: np.ndarray) -> list[tuple[float, float]]:
    centers = []
    if _CV2:
        params = cv2.SimpleBlobDetector_Params()
        params.filterByArea = True
        params.minArea = 10
        params.maxArea = 100000
        det = cv2.SimpleBlobDetector_create(params)
        kps = det.detect(img_gray)
        centers = [(float(kp.pt[0]), float(kp.pt[1])) for kp in kps]
    else:
        # coarse fallback
        ys, xs = np.where(img_gray < img_gray.mean() - 20)
        if len(xs):
            centers.append((float(xs.mean()), float(ys.mean())))
    return centers


def estimate_homography(src: list[tuple[float, float]], dst: list[tuple[float, float]]):
    if _CV2 and len(src) >= 4:
        H, _ = cv2.findHomography(np.array(src), np.array(dst), cv2.RANSAC)
        return H
    # least squares affine fallback
    if len(src) < 3:
        return np.eye(3)
    A = np.hstack([np.array(src), np.ones((len(src), 1))])
    Mx, *_ = np.linalg.lstsq(A, np.array(dst)[:, 0], rcond=None)
    My, *_ = np.linalg.lstsq(A, np.array(dst)[:, 1], rcond=None)
    H = np.eye(3)
    H[0] = Mx
    H[1] = My
    return H


def orientation_angle(img_gray: np.ndarray) -> float:
    if _CV2:
        _, bw = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        pts = np.column_stack(np.where(bw > 0)).astype(np.float32)
        if len(pts) < 10:
            return 0.0
        _mean, eig = cv2.PCACompute(pts, mean=None)
        return float(np.degrees(np.arctan2(eig[0, 1], eig[0, 0])))
    bw = (img_gray > img_gray.mean()).astype(float)
    ys, xs = np.where(bw > 0)
    if len(xs) < 10:
        return 0.0
    pts = np.column_stack([xs, ys]).astype(float)
    pts -= pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts, full_matrices=False)
    return float(np.degrees(np.arctan2(vt[0, 1], vt[0, 0])))
