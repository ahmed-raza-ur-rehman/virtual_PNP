"""FastAPI REST service exposing optimization and planning."""

from __future__ import annotations

try:
    from fastapi import FastAPI
    from pydantic import BaseModel

    _FASTAPI = True
except ImportError:
    _FASTAPI = False
    FastAPI = None

import numpy as np

from pnp.optimization.placement import optimize_placement
from pnp.planning.trajectory import plan_path

if _FASTAPI:
    app = FastAPI(title="Virtual PnP API", version="2.0.0")

    class TargetsIn(BaseModel):
        targets: list

    @app.post("/optimize/placement")
    def opt_placement(body: TargetsIn):
        return {"targets": optimize_placement(body.targets)}

    @app.post("/plan/path")
    def plan(body: dict):
        wps = np.array(body.get("waypoints", []), dtype=float)
        segs = plan_path(wps) if len(wps) > 1 else []
        return {"segments": len(segs), "samples": int(sum(len(s["t"]) for s in segs))}
else:
    app = None
