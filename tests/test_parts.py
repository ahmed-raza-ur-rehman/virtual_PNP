import os
import tempfile

from pnp.db.parts import PartsDB


def test_parts():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    db = PartsDB(path)
    db.add_part("R1", "Resistor 10k", "0402")
    assert db.get_part("R1")[1] == "Resistor 10k"
    os.remove(path)
