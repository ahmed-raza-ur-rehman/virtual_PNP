"""Tests for the netlist simulator and the RTL testbenches.

The full testbench suite is executed by ``make rtl-sim`` and writes its
evidence to ``verification/reports/sim/``.  Here the fast, self-contained
testbenches run as part of the python test suite so that a regression in the
simulator itself is caught immediately rather than at report time.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

HAS_YOSYS = bool(shutil.which("yosys") or shutil.which("yowasp-yosys")
                 or (ROOT / ".venv" / "bin" / "yowasp-yosys").exists())

pytestmark = pytest.mark.skipif(not HAS_YOSYS, reason="yosys is not installed")


def test_vcd_writer_emits_a_header(tmp_path):
    from rtlsim.vcd import VCDWriter

    with VCDWriter(tmp_path / "wave.vcd") as writer:
        writer.add("clk", 1)
        writer.add("count", 8)
        writer.step(0, {"clk": 0, "count": 0})
        writer.step(5, {"clk": 1, "count": 3})
    text = (tmp_path / "wave.vcd").read_text()
    assert "$enddefinitions" in text
    assert "b00000011" in text
    assert "#5" in text


def test_crc_testbench_passes(tmp_path):
    pytest.importorskip("rtlsim.testbenches")
    from rtlsim.testbenches import tb_crc_vectors

    result = tb_crc_vectors(None)
    assert result.status == "pass", result.failures


def test_divider_testbench_passes():
    from rtlsim.testbenches import tb_seq_div_random

    result = tb_seq_div_random(None)
    assert result.status == "pass", result.failures


def test_simulator_rejects_unknown_cells(tmp_path):
    import json

    from rtlsim.netlist import load_design
    from rtlsim.sim import SimError, Simulation

    design = {"modules": {"m": {"ports": {"a": {"direction": "input", "bits": [2]}},
                                "cells": {"c": {"type": "$_NAND3_", "connections": {
                                    "A": [2], "B": [2], "C": [2], "Y": [3]}}},
                                "netnames": {}}}}
    path = tmp_path / "m.json"
    path.write_text(json.dumps(design))
    loaded = load_design(path, "m")
    with pytest.raises(SimError):
        Simulation(loaded)
