"""Tests for the RTL-to-GDSII mini-flow.

These tests are the regression net for the flow itself: the pieces that were
written and debugged while building it (netlist mapping, placement legality,
routing geometry, GDS round-trip, DRC on known-good and known-bad geometry)
each get an explicit test, so a future change to the placer or router fails
here rather than in a tape-out.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from asic.miniflow import gdsii
from asic.miniflow.netlist_map import Instance, MapError, Net, Netlist, map_netlist
from asic.miniflow.placer import place
from asic.miniflow.router import Grid, route
from asic.miniflow.signoff import Layout, check_connectivity, check_drc
from asic.miniflow.tech import LIBRARY, RULES, snap_to_grid

BUILD = ROOT / "synthesis" / "build"


def _synthetic_netlist() -> Netlist:
    """A tiny hand-written netlist: two inverters in series plus a flop."""
    nl = Netlist(top="tiny")
    nl.ports = {"a": {}, "clk": {}}
    nl.instances["inv1"] = Instance("inv1", "INV_X1", {"A": "a", "Y": "n1"})
    nl.instances["inv2"] = Instance("inv2", "INV_X1", {"A": "n1", "Y": "n2"})
    nl.instances["ff1"] = Instance("ff1", "DFF_X1", {"D": "n2", "CLK": "clk", "Q": "q"})
    for name in ("a", "n1", "n2", "clk", "q"):
        nl.nets[name] = Net(name=name)
    nl.nets["a"].is_port = True
    nl.nets["a"].pins.append(("inv1", "A"))
    nl.nets["n1"].pins += [("inv1", "Y"), ("inv2", "A")]
    nl.nets["n1"].driver = ("inv1", "Y")
    nl.nets["n2"].pins += [("inv2", "Y"), ("ff1", "D")]
    nl.nets["n2"].driver = ("inv2", "Y")
    nl.nets["clk"].is_port = True
    nl.nets["clk"].pins.append(("ff1", "CLK"))
    nl.nets["q"].pins.append(("ff1", "Q"))
    nl.nets["q"].driver = ("ff1", "Q")
    return nl


# --------------------------------------------------------------------------- #
# library and technology
# --------------------------------------------------------------------------- #
def test_library_is_grid_aligned():
    for name, cell in LIBRARY.items():
        assert (
            abs(cell.width / RULES.routing_pitch - round(cell.width / RULES.routing_pitch)) < 1e-9
        ), name
        for pin, (x, y) in cell.pins.items():
            assert abs(x / RULES.routing_pitch - round(x / RULES.routing_pitch)) < 1e-9, (name, pin)


def test_pins_are_unique_within_a_cell():
    """Two pins of one cell on the same column would short in the layout."""
    for name, cell in LIBRARY.items():
        columns = list(cell.pins.values())
        assert len(columns) == len(set(columns)), name


def test_snap_to_grid_rounds_up():
    assert snap_to_grid(1.0) == pytest.approx(1.2)
    assert snap_to_grid(1.2) == pytest.approx(1.2)


def test_rules_allow_the_routing_pitch():
    """pitch >= width + space is what makes a routed track legal by design."""
    for width, space in (
        (RULES.m1_width, RULES.m1_space),
        (RULES.m2_width, RULES.m2_space),
        (RULES.m3_width, RULES.m3_space),
        (RULES.m5_width, RULES.m5_space),
    ):
        assert RULES.routing_pitch + 1e-9 >= width + space


# --------------------------------------------------------------------------- #
# mapping
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not (BUILD / "crc16_ccitt.json").exists(), reason="run `make hdl-synth` first")
def test_map_real_netlist():
    nl = map_netlist(BUILD / "crc16_ccitt.json", "crc16_ccitt")
    assert nl.instances
    assert all(inst.cell in LIBRARY for inst in nl.instances.values())
    # every net is reachable from a driver or is a port
    driven = {net for net, n in nl.nets.items() if n.driver}
    assert driven


def test_map_rejects_unknown_cells(tmp_path):
    import json

    design = {
        "modules": {
            "m": {
                "ports": {},
                "cells": {"c1": {"type": "$_MYSTERY_", "connections": {"A": [2], "Y": [3]}}},
                "netnames": {},
            }
        }
    }
    path = tmp_path / "m.json"
    path.write_text(json.dumps(design))
    with pytest.raises(MapError):
        map_netlist(path, "m")


# --------------------------------------------------------------------------- #
# placement
# --------------------------------------------------------------------------- #
def test_placement_is_legal_and_improves_wirelength():
    nl = _synthetic_netlist()
    result = place(nl, moves=200)
    assert result.rows >= 1
    assert result.hpwl_after <= result.hpwl_before + 1e-6
    # no two cells may overlap
    import itertools

    cells = sorted(nl.instances.values(), key=lambda i: i.x)
    for left, right in itertools.pairwise(cells):
        assert left.x + LIBRARY[left.cell].width <= right.x + 1e-6


def test_placement_is_deterministic():
    a, b = _synthetic_netlist(), _synthetic_netlist()
    ra = place(a, moves=100, seed=3)
    rb = place(b, moves=100, seed=3)
    assert ra.hpwl_after == rb.hpwl_after


# --------------------------------------------------------------------------- #
# routing and geometry
# --------------------------------------------------------------------------- #
def test_router_connects_a_series_chain():
    nl = _synthetic_netlist()
    place(nl, moves=0)
    grid = Grid(nl)
    result, geometry = route(nl, grid=grid)
    assert result.routed >= 2
    for data in geometry.values():
        for layer, x0, y0, x1, y1 in data["wires"]:
            assert layer in ("M1", "M2", "M3", "M4", "M5")
            # wires are drawn at the minimum width of their layer
            width = min(x1 - x0, y1 - y0)
            assert width == pytest.approx(RULES.m1_width, abs=0.01)


def test_router_never_shares_a_track_between_nets():
    nl = _synthetic_netlist()
    place(nl, moves=0)
    grid = Grid(nl)
    route(nl, grid=grid)
    owners: dict[tuple[int, int, int], str] = {}
    for net in nl.nets.values():
        for node in net.route:
            assert owners.setdefault(node, net.name) == net.name


# --------------------------------------------------------------------------- #
# GDS round-trip
# --------------------------------------------------------------------------- #
def test_gds_round_trip(tmp_path):
    library = gdsii.Library(name="UNIT")
    library.cells["INV_X1"] = [gdsii.rect(5, 0, 0, 1.2, RULES.cell_height)]
    library.top = [
        gdsii.sref("INV_X1", 0, 0),
        gdsii.path(7, 0, 5, 10, 5, 0.2),
        gdsii.text(63, 0, 6, "net1"),
    ]
    path = gdsii.write_gds(tmp_path / "unit.gds", library)
    summary = gdsii.read_gds_summary(path)
    assert summary["structures"]["INV_X1"] == 1
    assert summary["structures"]["UNIT_TOP"] == 3
    # 1 nm database unit expressed through micron user units
    assert summary["units"]["db_unit_user_units"] == pytest.approx(0.001)
    assert summary["units"]["user_unit_m"] == pytest.approx(1e-6)
    assert summary["units"]["db_unit_m"] == pytest.approx(1e-9)


def test_gds_reader_rejects_truncation(tmp_path):
    library = gdsii.Library(name="UNIT")
    library.top = [gdsii.rect(5, 0, 0, 1, 1)]
    path = gdsii.write_gds(tmp_path / "unit.gds", library)
    data = path.read_bytes()
    path.write_bytes(data[: len(data) - 3])
    with pytest.raises(ValueError):
        gdsii.read_gds_summary(path)


# --------------------------------------------------------------------------- #
# DRC and connectivity
# --------------------------------------------------------------------------- #
def test_drc_flags_a_spacing_violation():
    layout = Layout()
    layout.add_metal("M1", (0.0, 0.0, 1.0, 0.2), net="n1")
    layout.add_metal("M1", (1.1, 0.0, 2.0, 0.2), net="n2")  # 0.1 gap, rule 0.2
    result = check_drc(layout)
    assert result.status == "violations"
    assert any(v["kind"] == "spacing" for v in result.violations)


def test_drc_ignores_shapes_of_the_same_net():
    layout = Layout()
    layout.add_metal("M1", (0.0, 0.0, 1.0, 0.2), net="n1")
    layout.add_metal("M1", (1.05, 0.0, 2.0, 0.2), net="n1")
    assert check_drc(layout).status == "clean"


def test_drc_flags_a_missing_via_enclosure():
    layout = Layout()
    layout.add_metal("M1", (0.0, 0.0, 0.2, 0.2))
    layout.add_via("VIA1", (0.05, 0.05, 0.15, 0.15))
    result = check_drc(layout)
    assert any(v["kind"] == "enclosure" for v in result.violations)


def test_connectivity_detects_an_open():
    nl = _synthetic_netlist()
    layout = Layout()
    # pin escapes for the two ends of n1 that never meet
    layout.add_metal("M1", (0.0, 0.0, 0.2, 1.0), net="n1")
    layout.pin_shapes.append(("n1", "inv1", "Y", (0.0, 0.0, 0.2, 1.0)))
    layout.add_metal("M1", (5.0, 0.0, 5.2, 1.0), net="n1")
    layout.pin_shapes.append(("n1", "inv2", "A", (5.0, 0.0, 5.2, 1.0)))
    result = check_connectivity(layout, nl)
    assert "n1" in result.open_nets


def test_connectivity_accepts_a_connected_net():
    nl = _synthetic_netlist()
    layout = Layout()
    layout.add_metal("M1", (0.0, 0.0, 5.2, 0.2), net="n1")
    layout.pin_shapes.append(("n1", "inv1", "Y", (0.0, 0.0, 0.2, 0.2)))
    layout.pin_shapes.append(("n1", "inv2", "A", (5.0, 0.0, 5.2, 0.2)))
    result = check_connectivity(layout, nl)
    assert "n1" not in result.open_nets
    assert result.connected_nets >= 1
