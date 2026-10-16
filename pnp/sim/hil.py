"""Hardware-in-the-loop simulation bridge."""
from __future__ import annotations

from pnp.sim.machine_sim import MachineSim


class HILBridge:
    def __init__(self):
        self.sim = MachineSim()
        self.connected = False

    def connect(self, port: str):
        self.connected = True
        return True

    def step(self, dt, cmd):
        self.sim.step(dt, target_pos=cmd.get("pos"), target_z=cmd.get("z"))
        return {"pos": self.sim.pos.tolist(), "z": float(self.sim.nozzle_z)}
