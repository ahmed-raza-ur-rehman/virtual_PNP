"""Core domain models for the virtual SMD pick-and-place machine."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ComponentPackage(str, Enum):
    CHIP = "chip"
    LED = "led"
    TRANSISTOR = "transistor"
    IC = "ic"
    BGA = "bga"


class Component(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    package: ComponentPackage
    width_mm: float = Field(gt=0)
    depth_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)
    color: int = 0x808080


class Pose(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    r: float = 0.0  # rotation deg


class PlacementTarget(BaseModel):
    id: int
    component: str
    x: float
    y: float = 0.0
    z: float
    rotation_deg: float = 0.0
    placed: bool = False
    placed_at: Pose | None = None


class Feeder(BaseModel):
    id: str
    component: str
    count: int = Field(ge=0)
    max_count: int = Field(ge=0)
    width_mm: float = 8.0
    position: tuple[float, float] = (0.0, 0.0)


class MachineProfile(str, Enum):
    STANDARD = "standard"
    HIGH_SPEED = "high_speed"
    HIGH_ACCURACY = "high_accuracy"
    MULTI_HEAD = "multi_head"


class MachineConfig(BaseModel):
    profile: MachineProfile = MachineProfile.STANDARD
    work_area_mm: tuple[float, float] = (500.0, 400.0)
    xy_speed_mm_s: float = 200.0
    z_speed_mm_s: float = 150.0
    accel_mm_s2: float = 80.0
    damp: float = 0.92
    accuracy_factor: float = 1.0
    heads: int = 1
    jerk_limit_mm_s3: float = 500.0


class TrajectoryPoint(BaseModel):
    t: float
    x: float
    y: float
    z: float
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
