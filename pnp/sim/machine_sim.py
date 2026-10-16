"""Physics simulation of the pick-and-place machine."""
import numpy as np


class MachineSim:
    def __init__(self):
        self.pos = np.array([0.0, 0.0])  # x, z (mm)
        self.nozzle_z = 80.0
        self.vel = np.array([0.0, 0.0, 0.0])  # vx, vz, vz_axis
        self.vacuum = False
        self.held = None
        self.placed = 0

    def step(self, dt, target_pos=None, target_z=None, speed=2.0, accel=0.08, damp=0.92):
        if target_pos is not None:
            tp = np.asarray(target_pos, dtype=float)
            d = tp - self.pos
            dist = np.linalg.norm(d)
            if dist > 1e-6:
                self.vel[:2] += (d/dist) * accel * speed
            # damping
            self.vel[:2] *= damp
            self.pos += self.vel[:2] * dt
            # clamp speed
            sp = np.linalg.norm(self.vel[:2])
            if sp > speed*1.5:
                self.vel[:2] = self.vel[:2]/sp * speed*1.5
        if target_z is not None:
            dz = target_z - self.nozzle_z
            self.vel[2] += np.sign(dz) * accel * 1.5
            self.vel[2] *= damp
            self.nozzle_z += self.vel[2] * dt
            self.vel[2] = np.clip(self.vel[2], -3.0, 3.0)
        self.nozzle_z = np.clip(self.nozzle_z, 2.0, 140.0)
        self.pos[0] = np.clip(self.pos[0], -180, 220)
        self.pos[1] = np.clip(self.pos[1], -180, 180)

    def pick(self, comp_type):
        self.vacuum = True
        self.held = comp_type

    def place(self):
        self.vacuum = False
        self.held = None
        self.placed += 1
