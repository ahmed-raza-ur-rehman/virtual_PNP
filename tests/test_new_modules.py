import numpy as np

from pnp.calibration.machine import estimate_backlash, estimate_scale
from pnp.monitoring.telemetry import Telemetry
from pnp.optimization.multiobjective import nsga2
from pnp.sim.hil import HILBridge


def test_nsga2():
    pop = [np.array([np.random.rand(), np.random.rand()]) for _ in range(20)]
    def obj(ind):
        return (ind[0], 1 - ind[0])
    front = nsga2(pop, obj, generations=5)
    assert len(front) > 0


def test_calibration():
    s = estimate_scale([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert abs(s - 1.0) < 1e-9
    b = estimate_backlash([1, 2, 3], [1.1, 2.1, 3.1])
    assert b > 0


def test_telemetry():
    t = Telemetry()
    t.record(x=1, y=2)
    assert t.latest()["x"] == 1
    assert len(t.to_list()) == 1


def test_hil():
    h = HILBridge()
    h.connect("/dev/ttyUSB0")
    r = h.step(0.01, {"pos": (5, 5), "z": 10})
    assert "pos" in r
