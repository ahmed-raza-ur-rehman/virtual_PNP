"""Machine and camera calibration routines."""

from __future__ import annotations

import numpy as np


def calibrate_machine(grid_points, measured_points):
    """Compute affine correction (scale/offset/rotation) from measured vs ideal."""
    src = np.asarray(grid_points, dtype=float)
    dst = np.asarray(measured_points, dtype=float)
    # least squares affine
    A = np.hstack([src, np.ones((len(src), 1))])
    Mx, *_ = np.linalg.lstsq(A, dst[:, 0], rcond=None)
    My, *_ = np.linalg.lstsq(A, dst[:, 1], rcond=None)
    return np.vstack([Mx, My])


def apply_calibration(pt, M):
    p = np.array([pt[0], pt[1], 1.0])
    return (M @ p)[:2]
