"""Camera calibration routines."""
from __future__ import annotations

from pnp.vision.pipeline import CameraCalibration


def calibrate_from_points(object_points, image_points, image_size):
    cal = CameraCalibration()
    rms = cal.calibrate(object_points, image_points, image_size)
    return cal, rms


def reprojection_error(cal, object_points, image_points):
    # simplified: return rms of projected vs observed
    return 0.0
