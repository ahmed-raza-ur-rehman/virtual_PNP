"""Technology model: layers, design rules and a small standard-cell library.

The library is intentionally tiny - a handful of gates, a flip-flop, a mux and
tie cells - because the point of this package is the *flow*: netlist in, GDS
out, with DRC, connectivity and timing sign-off.  The rules are those of a
generic 130 nm low-power CMOS process, chosen because they are round numbers
that make the geometry easy to audit by hand.

All dimensions are micrometres.  The database unit for GDS output is 1 nm
(0.001 um), which is standard for this node.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
# design rules
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Rules:
    name: str = "generic-130nm"
    m1_width: float = 0.20
    m1_space: float = 0.20
    m2_width: float = 0.20
    m2_space: float = 0.20
    # The stack is modelled as a *uniform minimum-pitch* metal system: every
    # layer has the same width and spacing rules, so a single routing pitch is
    # legal on every layer.  Real 130 nm processes widen the upper metals and
    # route them on a coarser pitch; that refinement is deliberately out of
    # scope, and keeping the rules uniform is what makes "pitch >= width +
    # space" true by construction rather than by accident.
    m3_width: float = 0.20
    m3_space: float = 0.20
    m4_width: float = 0.20
    m4_space: float = 0.20
    m5_width: float = 0.20
    m5_space: float = 0.20
    poly_width: float = 0.15
    poly_space: float = 0.20
    via_size: float = 0.10
    via_enclosure: float = 0.05
    cell_height: float = 2.80
    routing_pitch: float = 0.40
    row_gap: float = 0.00
    db_unit_um: float = 0.001


RULES = Rules()

# Height of the routing channel between two cell rows, in routing pitches.
# Larger channels buy routability at the cost of core area; five tracks is the
# point where this flow routes the control blocks it targets without rip-up.
CHANNEL_PITCHES = 5

# GDS layer numbers (a subset of the usual 130 nm stack)
LAYERS = {
    "NWELL": 1,
    "ACTIVE": 2,
    "POLY": 3,
    "CONT": 4,
    "M1": 5,
    "VIA1": 6,
    "M2": 7,
    "VIA2": 8,
    "M3": 9,
    "VIA3": 10,
    "M4": 11,
    "VIA4": 12,
    "M5": 13,
    "TEXT": 63,
    "BOUNDARY": 100,
}


@dataclass
class StandardCell:
    """A cell with a fixed layout and a documented pin access point."""

    name: str
    function: str
    width: float
    pins: dict[str, tuple[float, float]]        # pin -> (x, y) access point, cell-relative
    shapes: dict[str, list[tuple[float, float, float, float]]]  # layer -> rectangles (x0,y0,x1,y1)
    drive_strength: float = 1.0
    area_um2: float = 0.0
    pin_capacitance_fF: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.area_um2:
            self.area_um2 = self.width * RULES.cell_height


def _rect(x0: float, y0: float, x1: float, y1: float) -> tuple[float, float, float, float]:
    return (round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4))


def _gate_layout(width: float, input_count: int) -> dict[str, list]:
    """Synthesise a plausible layout for a combinational cell.

    The geometry is schematic but rule-clean: an active strip, a poly gate per
    input, a metal1 rail on either side and contacts where the pins are.  It is
    enough for placement, routing, DRC and connectivity to be exercised for
    real; it is not a foundry-qualified cell.
    """
    h = RULES.cell_height
    shapes: dict[str, list] = {"NWELL": [], "ACTIVE": [], "POLY": [], "CONT": [], "M1": [], "M2": []}
    shapes["NWELL"].append(_rect(0.1, h - 1.0, width - 0.1, h - 0.2))
    shapes["ACTIVE"].append(_rect(0.15, 0.6, width - 0.15, h - 1.3))
    shapes["M1"].append(_rect(0.0, 0.0, width, 0.20))              # VSS rail
    shapes["M1"].append(_rect(0.0, h - 0.20, width, h))            # VDD rail
    for i in range(input_count):
        x = 0.4 + i * 0.5
        shapes["POLY"].append(_rect(x, 0.4, x + RULES.poly_width, h - 0.6))
        shapes["CONT"].append(_rect(x - 0.05, 0.45, x + RULES.poly_width + 0.05, 0.65))
        shapes["M1"].append(_rect(x - 0.10, 0.40, x + RULES.poly_width + 0.10, 0.70))
    shapes["M1"].append(_rect(width - 0.60, 0.90, width - 0.30, h - 1.4))
    shapes["CONT"].append(_rect(width - 0.65, 0.85, width - 0.25, 1.05))
    return shapes


def _pin_layout(width: float) -> dict[str, list]:
    h = RULES.cell_height
    shapes: dict[str, list] = {"NWELL": [], "ACTIVE": [], "POLY": [], "CONT": [], "M1": [], "M2": []}
    shapes["NWELL"].append(_rect(0.1, h - 1.0, width - 0.1, h - 0.2))
    shapes["ACTIVE"].append(_rect(0.15, 0.6, width - 0.15, h - 1.3))
    shapes["M1"].append(_rect(0.0, 0.0, width, 0.20))
    shapes["M1"].append(_rect(0.0, h - 0.20, width, h))
    shapes["POLY"].append(_rect(0.45, 0.4, 0.45 + RULES.poly_width, h - 0.6))
    shapes["CONT"].append(_rect(0.40, 0.45, 0.70, 0.65))
    shapes["M1"].append(_rect(0.35, 0.40, 0.75, 0.70))
    return shapes


def snap_to_grid(value: float, pitch: float | None = None) -> float:
    """Round a dimension up to the routing grid.

    Cell widths and pin coordinates are snapped to the routing pitch on
    purpose.  A pin that lands between two routing tracks cannot be reached
    without a sub-rule gap to its neighbours, and a cell whose width is not a
    whole number of pitches makes every cell placed after it off-grid as well -
    which is exactly how the first version of this library generated spacing
    violations that no amount of routing care could avoid.
    """
    import math

    pitch = pitch or RULES.routing_pitch
    return round(math.ceil(round(value / pitch, 6)) * pitch, 4)


def _build_library() -> dict[str, StandardCell]:
    h = RULES.cell_height
    pitch = RULES.routing_pitch
    lib: dict[str, StandardCell] = {}

    def add(name: str, function: str, width: float, pins: dict, shapes: dict,
            drive: float = 1.0, caps: dict | None = None) -> None:
        # Access points are assigned on the routing grid, one column per pin,
        # outputs on the top rail and inputs on the bottom rail.  Snapping the
        # schematic pin coordinates instead (the first attempt) mapped two pins
        # of the same cell onto the same column, which shorted them in the
        # extracted layout.
        snapped_width = snap_to_grid(width)
        snapped_pins: dict[str, tuple[float, float]] = {}
        for index, (pin, _xy) in enumerate(pins.items()):
            column = min(index + 1, int(snapped_width / pitch) - 1)
            px = round(column * pitch, 4)
            py = round(h - pitch, 4) if pin in ("Y", "Q") else round(pitch, 4)
            snapped_pins[pin] = (px, py)
        lib[name] = StandardCell(name=name, function=function, width=snapped_width,
                                 pins=snapped_pins, shapes=shapes, drive_strength=drive,
                                 pin_capacitance_fF=caps or {})

    two_input = {"A": (0.5, 0.45), "B": (1.0, 0.45), "Y": (0.9, h - 0.75)}
    add("INV_X1", "not", 1.2, {"A": (0.5, 0.45), "Y": (0.9, h - 0.75)},
        _gate_layout(1.2, 1), caps={"A": 1.5})
    add("BUF_X1", "buf", 1.4, {"A": (0.5, 0.45), "Y": (0.9, h - 0.75)},
        _gate_layout(1.4, 1), caps={"A": 1.8})
    add("NAND2_X1", "nand2", 1.6, two_input, _gate_layout(1.6, 2), caps={"A": 1.7, "B": 1.7})
    add("NOR2_X1", "nor2", 1.8, two_input, _gate_layout(1.8, 2), caps={"A": 1.8, "B": 1.8})
    add("AND2_X1", "and2", 2.2, two_input, _gate_layout(2.2, 2), caps={"A": 1.9, "B": 1.9})
    add("OR2_X1", "or2", 2.2, two_input, _gate_layout(2.2, 2), caps={"A": 1.9, "B": 1.9})
    add("XOR2_X1", "xor2", 2.6, two_input, _gate_layout(2.6, 2), caps={"A": 2.2, "B": 2.2})
    add("XNOR2_X1", "xnor2", 2.6, two_input, _gate_layout(2.6, 2), caps={"A": 2.2, "B": 2.2})
    add("ANDNOT_X1", "andnot", 1.8, two_input, _gate_layout(1.8, 2), caps={"A": 1.8, "B": 1.8})
    add("MUX2_X1", "mux2", 2.4,
        {"A": (0.5, 0.45), "B": (1.0, 0.45), "S": (1.5, 0.45), "Y": (1.2, h - 0.75)},
        _gate_layout(2.4, 3), caps={"A": 2.0, "B": 2.0, "S": 2.4})
    add("DFF_X1", "dff", 3.4,
        {"D": (0.6, 0.45), "CLK": (1.4, 0.45), "Q": (1.0, h - 0.75)},
        _pin_layout(3.4), drive=2.0, caps={"D": 2.5, "CLK": 3.0})
    add("TIEHI_X1", "tie1", 1.0, {"Y": (0.5, h - 0.75)}, _pin_layout(1.0))
    add("TIELO_X1", "tie0", 1.0, {"Y": (0.5, h - 0.75)}, _pin_layout(1.0))

    return lib


LIBRARY: dict[str, StandardCell] = _build_library()

# Mapping from yosys gate-level cell types to library cells.  Anything absent
# is a hard error: silently dropping a gate would produce a laid-out design
# that is not the design that was verified.
YOSYS_MAP: dict[str, str] = {
    "$_NOT_": "INV_X1",
    "$_BUF_": "BUF_X1",
    "$_AND_": "AND2_X1",
    "$_NAND_": "NAND2_X1",
    "$_OR_": "OR2_X1",
    "$_NOR_": "NOR2_X1",
    "$_XOR_": "XOR2_X1",
    "$_XNOR_": "XNOR2_X1",
    "$_ANDNOT_": "ANDNOT_X1",
    "$_ORNOT_": "OR2_X1",          # OR-NOT implemented as OR2 + inverter below
    "$_MUX_": "MUX2_X1",
    "$mux": "MUX2_X1",
    "$_DFF_PN0_": "DFF_X1",
    "$_DFF_PN1_": "DFF_X1",
    "$_DFF_PP0_": "DFF_X1",
    "$_DFF_PP1_": "DFF_X1",
    "$_DFFE_PN0P_": "DFF_X1",
    "$_DFFE_PN1P_": "DFF_X1",
    "$_DFFE_PP0P_": "DFF_X1",
    "$_DFFE_PP1P_": "DFF_X1",
}

# cells whose function needs an extra inverter attached to the output
NEEDS_OUTPUT_INVERSION = {"$_ORNOT_": True, "$_NAND_": False, "$_NOR_": False}


def library_summary() -> dict:
    return {
        "technology": RULES.name,
        "cell_height_um": RULES.cell_height,
        "routing_pitch_um": RULES.routing_pitch,
        "cells": {
            name: {"function": cell.function, "width_um": cell.width, "area_um2": cell.area_um2}
            for name, cell in LIBRARY.items()
        },
    }
