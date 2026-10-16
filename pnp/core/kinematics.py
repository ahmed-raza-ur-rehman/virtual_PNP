"""Kinematics for the gantry pick-and-place machine."""

from __future__ import annotations

import numpy as np

from .models import Pose


def forward_kinematics(joint: np.ndarray) -> Pose:
    """Joint (x,y,z,r) -> Cartesian pose (identity for Cartesian gantry)."""
    return Pose(x=float(joint[0]), y=float(joint[1]), z=float(joint[2]), r=float(joint[3]))


def inverse_kinematics(pose: Pose) -> np.ndarray:
    return np.array([pose.x, pose.y, pose.z, pose.r], dtype=float)


def workspace_check(pose: Pose, cfg) -> bool:
    x0, x1 = cfg.xy_range_x
    y0, y1 = cfg.xy_range_y
    z0, z1 = cfg.z_range
    return x0 <= pose.x <= x1 and y0 <= pose.y <= y1 and z0 <= pose.z <= z1
