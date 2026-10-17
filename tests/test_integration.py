"""End-to-end integration tests."""
import os
import tempfile

import numpy as np

from pnp.core.history import RunHistory
from pnp.ml.training import train_val_split
from pnp.optimization.feeding import optimize_feeders, optimize_turntable
from pnp.optimization.placement import optimize_placement
from pnp.planning.trajectory import plan_path
from pnp.sim.machine_sim import MachineSim
from pnp.vision.pipeline import orientation_angle


def test_full_pipeline():
    # 1. generate targets
    ts = [{"id": i, "type": "0402" if i % 2 == 0 else "0603",
           "x": float(i * 5), "z": float((i % 4) * 3), "placed": False} for i in range(20)]
    # 2. optimize
    opt = optimize_placement(ts)
    assert len(opt) == 20
    # 3. feeders
    feeders = [{"type": "0402", "count": 100}, {"type": "0603", "count": 80}]
    newf = optimize_feeders(opt, feeders)
    assert len(newf) == 2
    # 4. turntable
    tray = optimize_turntable(opt, slots=8)
    assert len(tray) == 8
    # 5. plan path
    wps = np.array([(t["x"], t["z"]) for t in opt[:5]])
    segs = plan_path(wps)
    assert len(segs) == 4
    # 6. vision
    img = np.zeros((32, 32), dtype=np.uint8)
    img[10:22, 14:18] = 200
    a = orientation_angle(img)
    assert isinstance(a, float)
    # 7. sim
    sim = MachineSim()
    sim.step(0.01, target_pos=(10, 10), target_z=5)
    sim.pick("0402")
    sim.place()
    assert sim.placed == 1
    # 8. history
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd); os.remove(path)
    h = RunHistory(path)
    h.record("standard", 1, 99.0, 100.0)
    assert len(h.recent()) == 1
    os.remove(path)


def test_ml_pipeline():
    rng = __import__("numpy").random.default_rng(0)
    X = rng.random((50, 8, 8))
    y = rng.integers(0, 3, 50)
    Xtr, Xva, _ytr, _yva = train_val_split(X, y)
    assert len(Xtr) + len(Xva) == 50
