import os
import tempfile

from pnp.core.history import RunHistory


def test_history():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    h = RunHistory(path)
    h.record("standard", 10, 99.5, 100.0, {"x": 1})
    rows = h.recent(5)
    assert len(rows) == 1
    assert rows[0]["placed"] == 10
    os.remove(path)
