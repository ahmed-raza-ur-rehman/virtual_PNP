from pnp.sim.machine_sim import MachineSim


def test_sim_step():
    m = MachineSim()
    m.step(0.01, target_pos=(10, 20), target_z=10)
    assert m.pos.shape == (2,)


def test_sim_pick_place():
    m = MachineSim()
    m.pick("0402")
    assert m.vacuum and m.held == "0402"
    m.place()
    assert not m.vacuum and m.held is None and m.placed == 1
