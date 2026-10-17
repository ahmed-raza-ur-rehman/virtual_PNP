import numpy as np

from pnp.control.motion_controller import MotionController, TrajectoryGenerator


def test_trajectory_gen():
    gen = TrajectoryGenerator(200, 100, 500)
    pts = gen.plan(np.array([0.0, 0.0, 0.0]), np.array([10.0, 0.0, 0.0]))
    assert len(pts) > 1
    assert np.allclose(pts[-1].position, [10.0, 0.0, 0.0], atol=0.5)


def test_motion_controller():
    mc = MotionController()
    mc.enable()
    mc.set_target([5.0, 3.0, 2.0])
    for _ in range(100):
        mc.update(0.001)
    st = mc.get_status()
    assert "position" in st
