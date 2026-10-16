from pnp.safety.monitor import SafetyMonitor


def test_safety():
    sm = SafetyMonitor(limits={"x": (-10, 10), "y": (-10, 10), "z": (0, 50)})
    sm.kick()
    assert sm.tick({"x": 0, "y": 0, "z": 10})
    assert sm.ok() if hasattr(sm, "ok") else not sm.e_stop
    sm.trigger_estop() if hasattr(sm, "trigger_estop") else sm._trip("estop")
    assert sm.e_stop
