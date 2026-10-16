"""Configuration management."""
from __future__ import annotations

import os
from dataclasses import dataclass

import yaml


@dataclass
class MachineConfig:
    profile: str = "standard"
    work_area: tuple[float, float] = (500.0, 400.0)
    xy_speed: float = 200.0
    z_speed: float = 150.0
    accel: float = 80.0
    damp: float = 0.92
    jerk: float = 500.0
    log_level: str = "INFO"

    @classmethod
    def from_yaml(cls, path: str) -> MachineConfig:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_env(cls) -> MachineConfig:
        cfg = cls()
        if "PnP_PROFILE" in os.environ:
            cfg.profile = os.environ["PnP_PROFILE"]
        return cfg
