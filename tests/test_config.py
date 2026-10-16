from pnp.core.config import MachineConfig


def test_default():
    c = MachineConfig()
    assert c.profile == "standard"


def test_from_env(monkeypatch):
    monkeypatch.setenv("PnP_PROFILE", "high_speed")
    c = MachineConfig.from_env()
    assert c.profile == "high_speed"
