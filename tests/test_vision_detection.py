import numpy as np

from pnp.vision.detection import compute_centroid, detect_components
from pnp.vision.tracking import track_components


def test_detect():
    img = np.zeros((64, 64), dtype=np.uint8)
    img[20:30, 20:30] = 255
    boxes = detect_components(img)
    assert len(boxes) >= 1


def test_centroid():
    c = compute_centroid((10, 10, 20, 20))
    assert c == (20.0, 20.0)


def test_track():
    prev = [(0, 0, 10, 10)]
    curr = [(2, 2, 10, 10)]
    m = track_components(prev, curr)
    assert 0 in m
