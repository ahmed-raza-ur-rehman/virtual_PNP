"""Dataset utilities for vision training."""
from __future__ import annotations

from pathlib import Path

import numpy as np


def load_images(folder: str):
    # placeholder: return list of paths
    return sorted(Path(folder).glob("*.png"))


def augment(img: np.ndarray) -> np.ndarray:
    # random flip/rotate
    if np.random.rand() > 0.5:
        img = np.fliplr(img)
    if np.random.rand() > 0.5:
        img = np.flipud(img)
    return img
