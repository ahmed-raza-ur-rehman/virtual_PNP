"""Domain exceptions."""
from __future__ import annotations


class PnPError(Exception):
    """Base exception for the virtual PnP platform."""


class WorkspaceViolation(PnPError):
    """Target pose outside the machine workspace."""


class FeederEmpty(PnPError):
    """Requested feeder has no components left."""


class VisionError(PnPError):
    """Vision pipeline failure."""


class PlanningError(PnPError):
    """Trajectory planning failure."""
