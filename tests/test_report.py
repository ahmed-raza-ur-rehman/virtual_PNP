import os
import tempfile

from pnp.reporting.report import generate_run_report


def test_report():
    fd, path = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    generate_run_report(path, {"placed": 10, "accuracy": 99.5})
    with open(path) as f:
        content = f.read()
    assert "placed" in content
    os.remove(path)
