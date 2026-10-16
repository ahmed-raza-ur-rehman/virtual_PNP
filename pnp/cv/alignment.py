"""Fiducial alignment and PCB registration."""
import numpy as np

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False


def find_fiducials(image_gray: np.ndarray, template=None):
    """Find fiducial markers (dark circles) and return their centers."""
    centers = []
    if _CV2:
        # simple blob detection
        params = cv2.SimpleBlobDetector_Params()
        params.filterByArea = True
        params.minArea = 20
        params.maxArea = 5000
        det = cv2.SimpleBlobDetector_create(params)
        kps = det.detect(image_gray)
        centers = [(kp.pt[0], kp.pt[1]) for kp in kps]
    else:
        # fallback: threshold + connected components via numpy (coarse)
        bw = image_gray < (image_gray.mean() - 20)
        # downsample not; just return centroid of dark region
        ys, xs = np.where(bw)
        if len(xs) > 0:
            centers.append((float(xs.mean()), float(ys.mean())))
    return centers


def compute_transform(src_pts, dst_pts):
    """Compute 2x3 affine transform from src to dst (least squares)."""
    src = np.asarray(src_pts, dtype=float)
    dst = np.asarray(dst_pts, dtype=float)
    if len(src) < 3:
        return np.eye(2, 3)
    # solve least squares
    A = np.hstack([src, np.ones((len(src), 1))])
    # for x and y separately
    Mx, *_ = np.linalg.lstsq(A, dst[:, 0], rcond=None)
    My, *_ = np.linalg.lstsq(A, dst[:, 1], rcond=None)
    return np.vstack([Mx, My])


def apply_transform(pt, M):
    p = np.array([pt[0], pt[1], 1.0])
    return (M @ p)[:2]
