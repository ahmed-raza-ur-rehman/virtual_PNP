import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from pnp.optimization.placement import optimize_placement
from pnp.planning.trajectory import collision_free


@given(st.lists(st.tuples(st.floats(-100, 100), st.floats(-100, 100)), min_size=1, max_size=20))
def test_optimize_preserves_count(pts):
    ts = [{"id": i, "type": "0402", "x": p[0], "z": p[1], "placed": False} for i, p in enumerate(pts)]
    opt = optimize_placement(ts)
    assert len(opt) == len(ts)


@given(st.floats(0, 50), st.floats(0, 50))
def test_collision_free_straight(a, b):
    pts = np.array([[0.0, 0.0], [a, b]], dtype=float)
    # obstacle far away
    assert collision_free(pts, [(1000.0, 1000.0, 1.0)])
