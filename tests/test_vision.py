import numpy as np

from pnp.vision.pipeline import detect_fiducials, estimate_homography, orientation_angle


def test_detect_fiducials():
    img = np.zeros((64, 64), dtype=np.uint8)
    img[20:30, 20:30] = 50
    centers = detect_fiducials(img)
    assert isinstance(centers, list)


def test_orientation_angle():
    img = np.zeros((64, 64), dtype=np.uint8)
    img[20:44, 28:36] = 200
    a = orientation_angle(img)
    assert isinstance(a, float)


def test_homography():
    src = [(0, 0), (10, 0), (10, 10), (0, 10)]
    dst = [(1, 1), (11, 1), (11, 11), (1, 11)]
    H = estimate_homography(src, dst)
    assert H.shape == (3, 3)
