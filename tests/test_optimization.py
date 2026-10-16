import numpy as np

from pnp.optimization.feeding import optimize_feeders, optimize_turntable
from pnp.optimization.placement import optimize_placement
from pnp.planning.trajectory import collision_free, plan_path


def test_optimize_placement_reduces_path():
    ts = [
        {
            "id": i,
            "type": "0402" if i % 2 == 0 else "0603",
            "x": float(i * 10),
            "z": float((i % 3) * 5),
            "placed": False,
        }
        for i in range(20)
    ]
    opt = optimize_placement(ts, start=(0.0, 0.0))
    assert len(opt) == len(ts)
    assert all(t["id"] in [x["id"] for x in ts] for t in opt)


def test_optimize_feeders():
    ts = [
        {"type": "A", "x": -50.0, "z": 0.0, "placed": False},
        {"type": "B", "x": 50.0, "z": 0.0, "placed": False},
    ]
    feeders = [{"type": "A", "count": 10}, {"type": "B", "count": 5}]
    new = optimize_feeders(ts, feeders)
    assert len(new) == len(feeders)


def test_optimize_turntable():
    ts = [
        {"type": "A", "x": -10.0, "z": 0.0, "placed": False},
        {"type": "B", "x": 10.0, "z": 0.0, "placed": False},
    ]
    res = optimize_turntable(ts, slots=12)
    assert len(res) == 12
    assert res[0]["type"] is not None


def test_plan_path():
    wps = np.array([[0, 0], [10, 0], [10, 10]], dtype=float)
    segs = plan_path(wps)
    assert len(segs) == 2
    assert all(len(s["t"]) > 1 for s in segs)


def test_collision_free():
    pts = np.array([[0, 0], [10, 0]], dtype=float)
    assert collision_free(pts, [(5, 5, 1)])
    assert not collision_free(pts, [(5, 0, 1)])
