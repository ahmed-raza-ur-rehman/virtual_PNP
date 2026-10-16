"""Computer vision: component orientation detection."""
import numpy as np

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False


def detect_orientation_angle(image_gray: np.ndarray) -> float:
    """Estimate dominant orientation angle (degrees) via image moments/PCA."""
    if _CV2:
        # threshold
        _, bw = cv2.threshold(image_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        pts = np.column_stack(np.where(bw > 0))
        if len(pts) < 10:
            return 0.0
        # PCA
        pts = pts.astype(np.float32)
        _mean, eigenvectors = cv2.PCACompute(pts, mean=None)
        angle = np.degrees(np.arctan2(eigenvectors[0, 1], eigenvectors[0, 0]))
        return float(angle)
    # fallback: use numpy SVD on thresholded image
    bw = (image_gray > image_gray.mean()).astype(float)
    ys, xs = np.where(bw > 0)
    if len(xs) < 10:
        return 0.0
    pts = np.column_stack([xs, ys]).astype(float)
    pts -= pts.mean(axis=0)
    _u, _s, vt = np.linalg.svd(pts, full_matrices=False)
    angle = np.degrees(np.arctan2(vt[0, 1], vt[0, 0]))
    return float(angle)


def classify_component(image_gray: np.ndarray) -> str:
    """Simple rule-based component classifier by aspect ratio."""
    h, w = image_gray.shape[:2]
    ar = w / max(h, 1)
    if ar > 2.5:
        return "1206/0805 chip"
    if ar > 1.5:
        return "0603/0402 chip"
    if 0.9 < ar < 1.1:
        return "QFN/SOIC"
    return "unknown"
