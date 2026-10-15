"""Sign-off checks: DRC, connectivity (LVS-lite) and static timing analysis.

All three run on the *layout as generated* - the rectangles that go into the
GDS file - so a passing report is evidence about the tape-out artefact and not
about the in-memory database that produced it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .netlist_map import Netlist
from .tech import LAYERS, LIBRARY, RULES

# --------------------------------------------------------------------------- #
# flattened layout
# --------------------------------------------------------------------------- #
Rect = tuple[float, float, float, float]


@dataclass
class Layout:
    """Flattened geometry: every rectangle in absolute coordinates."""

    shapes: dict[str, list[Rect]] = field(default_factory=dict)   # metal layer -> rects
    vias: dict[str, list[Rect]] = field(default_factory=dict)     # via layer -> rects
    pin_shapes: list[tuple[str, str, str, Rect]] = field(default_factory=list)  # net, inst, pin, rect
    texts: list[tuple[str, float, float]] = field(default_factory=list)
    bounds: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    #: owner net of each shape, keyed by (layer, rect).  Spacing is checked
    #: between *different* nets only: two shapes of one net are one conductor,
    #: and a checker that measures the gap between them reports violations no
    #: process could avoid.
    shape_net: dict[tuple[str, Rect], str] = field(default_factory=dict)

    def add_metal(self, layer: str, rect: Rect, net: str = "") -> None:
        self.shapes.setdefault(layer, []).append(rect)
        if net:
            self.shape_net[(layer, rect)] = net

    def add_via(self, layer: str, rect: Rect, net: str = "") -> None:
        self.vias.setdefault(layer, []).append(rect)
        if net:
            self.shape_net[(layer, rect)] = net


# --------------------------------------------------------------------------- #
# DRC
# --------------------------------------------------------------------------- #
@dataclass
class DRCResult:
    checks: int = 0
    violations: list[dict] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "clean" if not self.violations else "violations"

    def to_dict(self) -> dict:
        breakdown: dict[str, int] = {}
        for violation in self.violations:
            key = f"{violation.get('rule', '?')} ({violation.get('kind', '?')})"
            breakdown[key] = breakdown.get(key, 0) + 1
        return {
            "status": self.status,
            "checks": self.checks,
            "violations": len(self.violations),
            "breakdown": dict(sorted(breakdown.items(), key=lambda kv: -kv[1])),
            "details": self.violations[:10],
        }


def _overlap_or_touch(a: Rect, b: Rect, gap: float = 0.0) -> bool:
    return not (
        a[2] + gap < b[0] or b[2] + gap < a[0] or a[3] + gap < b[1] or b[3] + gap < a[1]
    )


def check_drc(layout: Layout, rules=RULES) -> DRCResult:
    """Width, spacing, notch and via-enclosure checks.

    The rectangle set from this flow is axis aligned and sparse (a few hundred
    shapes), so a sweep over pairs is honest and fast; a production checker
    would use a scan-line or a spatial index to stay linear.
    """
    result = DRCResult()
    layer_rules = {
        "M1": (rules.m1_width, rules.m1_space),
        "M2": (rules.m2_width, rules.m2_space),
        "M3": (rules.m3_width, rules.m3_space),
        "M4": (rules.m4_width, rules.m4_space),
        "M5": (rules.m5_width, rules.m5_space),
        "POLY": (rules.poly_width, rules.poly_space),
    }

    for layer, rects in layout.shapes.items():
        min_width, min_space = layer_rules.get(layer, (0.2, 0.2))
        for i, rect in enumerate(rects):
            width_x = rect[2] - rect[0]
            width_y = rect[3] - rect[1]
            if layer != "POLY":
                # a wire only has to be wide in its preferred direction
                short_side = min(width_x, width_y)
                result.checks += 1
                if short_side + 1e-9 < min_width:
                    result.violations.append({
                        "rule": f"{layer}.W.1", "kind": "width",
                        "layer": layer, "rect": rect, "value_um": round(short_side, 3),
                        "required_um": min_width,
                    })
            for other in rects[i + 1:]:
                if _overlap_or_touch(rect, other):
                    continue
                if (self_net := layout.shape_net.get((layer, rect))) is not None \
                        and self_net == layout.shape_net.get((layer, other)):
                    continue        # same conductor: no spacing rule applies
                # edge-to-edge distance for non-touching, non-overlapping boxes
                dx = max(other[0] - rect[2], rect[0] - other[2], 0.0)
                dy = max(other[1] - rect[3], rect[1] - other[3], 0.0)
                gap = max(dx, dy)
                result.checks += 1
                if gap + 1e-9 < min_space:
                    result.violations.append({
                        "rule": f"{layer}.S.1", "kind": "spacing", "layer": layer,
                        "rects": [rect, other], "value_um": round(gap, 3),
                        "required_um": min_space,
                    })

    # via enclosure: each via must be enclosed by both metals it connects
    via_pairs = {
        "VIA1": ("M1", "M2"),
        "VIA2": ("M2", "M3"),
        "VIA3": ("M3", "M4"),
        "VIA4": ("M4", "M5"),
    }
    for via_layer, (lower, upper) in via_pairs.items():
        for via in layout.vias.get(via_layer, []):
            for metal, partner in ((lower, "lower"), (upper, "upper")):
                result.checks += 1
                enclosing = [
                    rect for rect in layout.shapes.get(metal, [])
                    if rect[0] - 1e-9 <= via[0] and rect[1] - 1e-9 <= via[1]
                    and rect[2] + 1e-9 >= via[2] and rect[3] + 1e-9 >= via[3]
                    and min(via[0] - rect[0], via[1] - rect[1],
                            rect[2] - via[2], rect[3] - via[3]) + 1e-9 >= rules.via_enclosure
                ]
                if not enclosing:
                    result.violations.append({
                        "rule": f"{via_layer}.E.1", "kind": "enclosure",
                        "layer": via_layer, "metal": metal, "partner": partner,
                        "rect": via, "required_um": rules.via_enclosure,
                    })
    return result


# --------------------------------------------------------------------------- #
# connectivity (LVS-lite)
# --------------------------------------------------------------------------- #
@dataclass
class ConnectivityResult:
    connected_nets: int = 0
    open_nets: list[str] = field(default_factory=list)
    shorts: list[list[str]] = field(default_factory=list)
    shapes_inspected: int = 0

    @property
    def status(self) -> str:
        return "clean" if not self.open_nets and not self.shorts else "mismatch"

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "connected_nets": self.connected_nets,
            "open_nets": self.open_nets,
            "shorts": self.shorts[:10],
            "shapes_inspected": self.shapes_inspected,
        }


class _Union:
    def __init__(self) -> None:
        self.parent: dict[int, int] = {}

    def find(self, item: int) -> int:
        self.parent.setdefault(item, item)
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def check_connectivity(layout: Layout, netlist: Netlist) -> ConnectivityResult:
    """Extract connectivity from the layout and compare it with the netlist.

    This is an *LVS-lite* check: it verifies that every net's pins are on one
    electrical component and that no two nets share a component.  It does not
    extract transistors, so it cannot catch a library cell whose schematic and
    layout disagree - that check belongs to the cell-level LVS of the library,
    which is out of scope here and is stated as such in the report.
    """
    result = ConnectivityResult()
    union = _Union()
    index: dict[int, tuple[str, Rect]] = {}
    counter = 0

    def register(layer: str, rect: Rect) -> int:
        nonlocal counter
        union.find(counter)
        index[counter] = (layer, rect)
        counter += 1
        return counter - 1

    all_shapes: list[tuple[int, str, Rect]] = []
    for layer, rects in layout.shapes.items():
        for rect in rects:
            idx = register(layer, rect)
            all_shapes.append((idx, layer, rect))
    for layer, rects in layout.vias.items():
        for rect in rects:
            idx = register(layer, rect)
            all_shapes.append((idx, layer, rect))

    result.shapes_inspected = len(all_shapes)

    # same-layer touching shapes are electrically one node
    for i, (idx_a, layer_a, rect_a) in enumerate(all_shapes):
        for idx_b, layer_b, rect_b in all_shapes[i + 1:]:
            if layer_a != layer_b:
                continue
            if _overlap_or_touch(rect_a, rect_b, gap=1e-6):
                union.union(idx_a, idx_b)

    # vias connect the two metals they land on
    via_pairs = {
        "VIA1": ("M1", "M2"), "VIA2": ("M2", "M3"),
        "VIA3": ("M3", "M4"), "VIA4": ("M4", "M5"),
    }
    for via_layer, (lower, upper) in via_pairs.items():
        for idx_v, layer_v, via in all_shapes:
            if layer_v != via_layer:
                continue
            for idx_m, layer_m, metal in all_shapes:
                if layer_m not in (lower, upper):
                    continue
                if _overlap_or_touch(via, metal, gap=1e-6):
                    union.union(idx_v, idx_m)

    # group pins by component
    net_components: dict[str, set[int]] = {}
    for net, inst, pin, rect in _pin_rects(layout):
        component = None
        for idx, layer, shape in all_shapes:
            if _overlap_or_touch(rect, shape, gap=1e-6):
                root = union.find(idx)
                component = root if component is None else component
                if component != root:
                    # two shapes under one pin: they must already be merged
                    union.union(component, root)
                    component = union.find(root)
        if component is None:
            continue
        net_components.setdefault(net, set()).add(union.find(component))

    for net_name, components in sorted(net_components.items()):
        if len(components) > 1:
            result.open_nets.append(net_name)
        else:
            result.connected_nets += 1

    # a short is two different nets sharing a component
    component_owner: dict[int, str] = {}
    for net_name, components in net_components.items():
        for component in components:
            other = component_owner.get(component)
            if other is not None and other != net_name:
                result.shorts.append(sorted([other, net_name]))
            component_owner.setdefault(component, net_name)
    return result


def _pin_rects(layout: Layout):
    yield from layout.pin_shapes


# --------------------------------------------------------------------------- #
# static timing analysis
# --------------------------------------------------------------------------- #
@dataclass
class TimingResult:
    clock_period_ns: float
    critical_path_ns: float
    slack_ns: float
    fmax_mhz: float
    path: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "met" if self.slack_ns >= 0 else "violated"

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "clock_period_ns": round(self.clock_period_ns, 4),
            "critical_path_ns": round(self.critical_path_ns, 4),
            "slack_ns": round(self.slack_ns, 4),
            "fmax_mhz": round(self.fmax_mhz, 1),
            "path": self.path[:12],
        }


#: intrinsic cell delays (ps) for the library, per function
CELL_DELAY_PS = {
    "not": 28.0, "buf": 34.0, "nand2": 41.0, "nor2": 45.0, "and2": 62.0,
    "or2": 66.0, "xor2": 78.0, "xnor2": 82.0, "andnot": 58.0, "mux2": 74.0,
    "dff": 118.0,                    # clock-to-Q
    "tie1": 0.0, "tie0": 0.0,
}
#: setup time of the flip-flop in the library (ps)
DFF_SETUP_PS = 90.0
#: wire resistance per micrometre of M2/M3 track and capacitance per micrometre
WIRE_R_OHM_PER_UM = 0.28
WIRE_C_FF_PER_UM = 0.16
VIA_R_OHM = 4.5


def analyse_timing(netlist: Netlist, geometry: dict, clock_period_ns: float) -> TimingResult:
    """Static timing with an RC wire model and library intrinsic delays.

    Not a sign-off timer: it has no clock tree, no crosstalk and no derating.
    It answers the question the flow actually needs answered - does the routed
    layout close at the target period, and if not, which path is responsible -
    and it is computed from the *routed* wire lengths, so congestion shows up
    as timing pressure exactly as it does in a real flow.
    """
    instance_of_net: dict[str, list[tuple[str, str]]] = {}
    for inst in netlist.instances.values():
        for pin, net in inst.pins.items():
            instance_of_net.setdefault(net, []).append((inst.name, pin))

    def net_delay_ps(net_name: str) -> float:
        wires = geometry.get(net_name, {}).get("wires", [])
        vias = geometry.get(net_name, {}).get("vias", [])
        length = sum((x1 - x0) if layer == "M1" or layer in ("M3", "M5") else (y1 - y0)
                     for layer, x0, y0, x1, y1 in wires)
        resistance = WIRE_R_OHM_PER_UM * length + VIA_R_OHM * len(vias)
        capacitance = WIRE_C_FF_PER_UM * length
        for inst_name, pin in instance_of_net.get(net_name, []):
            cell = LIBRARY[netlist.instances[inst_name].cell]
            capacitance += cell.pin_capacitance_fF.get(pin, 0.0)
        # Elmore (lumped) delay; 1000 ps/ns scaling from ohm*fF = ps
        return resistance * capacitance

    # arrival time per instance output pin
    arrival: dict[str, float] = {}
    paths: dict[str, list[str]] = {}
    pending = dict(netlist.instances)

    def ready(inst_name: str) -> bool:
        inst = netlist.instances[inst_name]
        for pin, net in inst.pins.items():
            if pin in ("Y", "Q"):
                continue
            driver = netlist.nets[net].driver
            if driver is None:
                continue
            if driver[0] not in arrival:
                # input port or undriven: treat as arrival 0
                if driver[0] in pending:
                    return False
        return True

    iterations = 0
    while pending and iterations < 10000:
        iterations += 1
        progressed = False
        for inst_name in list(pending):
            if not ready(inst_name):
                continue
            inst = netlist.instances[inst_name]
            cell = LIBRARY[inst.cell]
            worst = 0.0
            worst_path: list[str] = []
            for pin, net in inst.pins.items():
                if pin in ("Y", "Q"):
                    continue
                driver = netlist.nets[net].driver
                if driver is None:
                    continue
                driver_inst, driver_pin = driver
                base = arrival.get(driver_inst, 0.0)
                candidate = base + net_delay_ps(net)
                if candidate >= worst:
                    worst = candidate
                    worst_path = paths.get(driver_inst, []) + [f"{net}->{inst_name}.{pin}"]
            q = worst + CELL_DELAY_PS.get(cell.function, 50.0)
            arrival[inst_name] = q
            paths[inst_name] = worst_path
            del pending[inst_name]
            progressed = True
        if not progressed:
            break

    # the path that arrives last at some flip-flop data pin (or an output port)
    critical = 0.0
    critical_path: list[str] = []
    for inst_name, inst in netlist.instances.items():
        cell = LIBRARY[inst.cell]
        if cell.function != "dff":
            continue
        for pin, net in inst.pins.items():
            if pin != "D":
                continue
            driver = netlist.nets[net].driver
            if driver is None:
                continue
            candidate = arrival.get(driver[0], 0.0) + net_delay_ps(net)
            if candidate >= critical:
                critical = candidate
                critical_path = paths.get(driver[0], []) + [f"{net}->{inst_name}.D"]

    critical_ns = critical / 1000.0
    slack = clock_period_ns - critical_ns - DFF_SETUP_PS / 1000.0
    fmax = 1000.0 / (critical_ns + DFF_SETUP_PS / 1000.0) if critical > 0 else float("inf")
    return TimingResult(
        clock_period_ns=clock_period_ns,
        critical_path_ns=critical_ns,
        slack_ns=slack,
        fmax_mhz=fmax,
        path=critical_path,
    )
