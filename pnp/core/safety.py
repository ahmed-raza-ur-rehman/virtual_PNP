"""Safety interlocks and limit checking."""
from __future__ import annotations

from .exceptions import WorkspaceViolation


def check_workspace(x, y, z, limits):
    if not (limits["x"][0] <= x <= limits["x"][1]):
        raise WorkspaceViolation(f"X {x} out of range")
    if not (limits["y"][0] <= y <= limits["y"][1]):
        raise WorkspaceViolation(f"Y {y} out of range")
    if not (limits["z"][0] <= z <= limits["z"][1]):
        raise WorkspaceViolation(f"Z {z} out of range")
    return True


def emergency_stop(state):
    state["estop"] = True
    state["motion_enabled"] = False
    return state
