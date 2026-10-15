#!/usr/bin/env python3
"""RTL-to-GDSII mini-flow: netlist in, checked GDS out.

Stages
------
``synthesise``  yosys elaborates and maps the RTL to a gate netlist (JSON)
``map``         gates mapped onto the standard-cell library in ``tech.py``
``place``       row-based placement with annealing on wire length
``route``       two-to-five metal maze routing with retry passes
``emit``        GDSII written from the placed, routed layout
``drc``         width, spacing and via-enclosure checks on the emitted shapes
``connectivity``layout extracted and compared net by net with the netlist
``timing``      RC-based static timing against the target clock period

The flow writes ``<out>/<design>.gds``, a JSON database and a Markdown report.
Every stage states its result, including the ones that did not close: a flow
that reports "routed" when it is not is worse than no flow at all.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from asic.miniflow import gdsii
from asic.miniflow.netlist_map import map_netlist
from asic.miniflow.placer import place
from asic.miniflow.router import Grid, route
from asic.miniflow.signoff import (Layout, analyse_timing, check_connectivity,
                                   check_drc)
from asic.miniflow.tech import LAYERS, LIBRARY, RULES, library_summary

#: designs the flow knows how to build, with the files and the top module
DESIGNS = {
    "crc16_ccitt": {
        "top": "crc16_ccitt",
        "files": ["rtl/comm/crc16_ccitt.sv"],
        "clock_period_ns": 10.0,
        "params": {},
    },
    "uart_tx": {
        "top": "uart_tx",
        "files": ["rtl/comm/uart_tx.sv"],
        "clock_period_ns": 10.0,
        "params": {"CLK_HZ": 100_000_000, "BAUD": 115_200},
    },
    "watchdog_wwdg": {
        "top": "watchdog_wwdg",
        "files": ["rtl/safety/watchdog_wwdg.sv"],
        "clock_period_ns": 10.0,
        "params": {"WIN_LOW": 100, "WIN_HIGH": 100_000},
    },
    "stepgen": {
        "top": "stepgen",
        "files": ["rtl/motion/stepgen.sv"],
        "clock_period_ns": 10.0,
        "params": {},
    },
    # A light-weight variant of the top level, used to show the flow running on
    # a multi-block design.  The full core needs buffer insertion on the reset
    # and clock nets, which this flow deliberately does not do (see docs).
    "pnp_core": {
        "top": "pnp_core",
        "files": [
            "rtl/common/seq_div.sv",
            "rtl/motion/quad_decoder.sv",
            "rtl/motion/profile_gen.sv",
            "rtl/motion/pid_axis.sv",
            "rtl/motion/stepgen.sv",
            "rtl/motion/axis_ctrl.sv",
            "rtl/comm/crc16_ccitt.sv",
            "rtl/comm/packet_if.sv",
            "rtl/comm/uart_tx.sv",
            "rtl/comm/uart_rx.sv",
            "rtl/comm/spi_slave.sv",
            "rtl/periph/csr_bank.sv",
            "rtl/safety/watchdog_wwdg.sv",
            "rtl/safety/limit_monitor.sv",
            "rtl/vision/centroid_accel.sv",
            "rtl/top/pnp_core.sv",
        ],
        "clock_period_ns": 10.0,
        "params": {"N_AXES": 1, "TELEM_DIV": 1000},
    },
}


def find_yosys() -> str:
    for candidate in (ROOT / "tools" / "bin" / "yosys", ROOT / ".venv" / "bin" / "yowasp-yosys"):
        if candidate.exists():
            return str(candidate)
    raise SystemExit("yosys not found - run scripts/bootstrap.sh")


def synthesise(design: str, build_dir: Path) -> Path:
    """Run yosys for one design and return the JSON netlist path."""
    spec = DESIGNS[design]
    build_dir.mkdir(parents=True, exist_ok=True)
    out = build_dir / f"{design}.json"
    files = " ".join(spec["files"])
    chparams = " ".join(f"-chparam {k} {v}" for k, v in spec["params"].items())
    script = "; ".join([
        f"read_verilog -sv -I rtl/common {files}",
        f"hierarchy -top {spec['top']} {chparams}".strip(),
        f"synth -top {spec['top']} -flatten",
        f"write_json {out.relative_to(ROOT)}",
        "stat",
    ])
    subprocess.run([find_yosys(), "-q", "-p", script], cwd=ROOT, check=True,
                   capture_output=True)
    return out


#: metal landing pad at every via.  It is exactly the track width, which is
#: the largest pad that still leaves the spacing rule intact between adjacent
#: tracks (pad 0.20 + space 0.20 = pitch 0.40).
VIA_PAD_UM = RULES.m1_width


def build_layout(netlist, geometry, grid=None) -> Layout:
    """Flatten the routed wires, via pads and pin escapes into geometry.

    Only the *signal* geometry goes into the extracted layout: the cells'
    internal shapes (including their VDD/VSS rails) live in the GDS cell
    structures, and the rails of abutting cells would otherwise merge every
    instance into one electrical node - which is correct physics for a power
    rail and wrong for a net-by-net comparison.  Connectivity extraction here
    therefore works on the same geometry a router produces.
    """
    layout = Layout()
    grid = grid or Grid(netlist)

    # routed wires
    for net_name, data in geometry.items():
        for layer, x0, y0, x1, y1 in data["wires"]:
            layout.add_metal(layer, (x0, y0, x1, y1), net=net_name)

    # via landing pads on both metals, then the via itself
    half_via = RULES.via_size / 2.0
    half_pad = VIA_PAD_UM / 2.0
    metal_of_via = {"VIA1": ("M1", "M2"), "VIA2": ("M2", "M3"),
                    "VIA3": ("M3", "M4"), "VIA4": ("M4", "M5")}
    for net_name, data in geometry.items():
        for via_layer, x, y in data["vias"]:
            layout.add_via(via_layer, (x - half_via, y - half_via, x + half_via, y + half_via),
                           net=net_name)
            for metal in metal_of_via.get(via_layer, ()):
                layout.add_metal(metal, (x - half_pad, y - half_pad, x + half_pad, y + half_pad),
                                 net=net_name)

    # pin escapes: pin -> M1 stub -> via -> access node in the channel
    for inst in netlist.instances.values():
        cell = LIBRARY[inst.cell]
        for pin, net in inst.pins.items():
            if pin not in cell.pins:
                continue
            px, py = cell.pins[pin]
            x, y = inst.x + px, inst.y + py
            access = netlist.nets[net].pin_nodes.get((inst.name, pin)) \
                or grid.access_nodes(netlist, inst.name, pin, fan=0)[0]
            ax, ay = grid.xy(access[0], access[1])
            stub = (x - RULES.m1_width / 2, y,
                    x + RULES.m1_width / 2, ay + RULES.m1_width / 2)
            layout.add_metal("M1", stub, net=net)
            layout.add_via("VIA1", (ax - half_via, ay - half_via, ax + half_via, ay + half_via),
                           net=net)
            layout.add_metal("M1", (ax - half_pad, ay - half_pad, ax + half_pad, ay + half_pad),
                             net=net)
            layout.add_metal("M2", (ax - half_pad, ay - half_pad, ax + half_pad, ay + half_pad),
                             net=net)
            layout.pin_shapes.append((net, inst.name, pin, stub))
            layout.texts.append((net, x, y))
    return layout


def build_gds_library(netlist, layout) -> gdsii.Library:
    """Translate the flattened layout into GDS structures."""
    library = gdsii.Library(name="PNP_MINIFLOW")
    # one structure per library cell, at its own origin
    for name, cell in LIBRARY.items():
        elements = []
        for layer, rects in cell.shapes.items():
            for (x0, y0, x1, y1) in rects:
                elements.append(gdsii.rect(LAYERS[layer], x0, y0, x1, y1))
        library.cells[name] = elements

    for inst in netlist.instances.values():
        library.top.append(gdsii.sref(inst.cell, inst.x, inst.y))

    for layer, rects in layout.shapes.items():
        if layer in ("POLY", "ACTIVE", "NWELL", "CONT"):
            continue                      # cell-internal: already in the cell structures
        for (x0, y0, x1, y1) in rects:
            library.top.append(gdsii.rect(LAYERS[layer], x0, y0, x1, y1))
    for layer, rects in layout.vias.items():
        for (x0, y0, x1, y1) in rects:
            library.top.append(gdsii.rect(LAYERS[layer], x0, y0, x1, y1))

    for name, x, y in layout.texts:
        library.top.append(gdsii.text(LAYERS["TEXT"], x, y, name))

    x0, y0, x1, y1 = layout.bounds
    library.top.append(gdsii.rect(LAYERS["BOUNDARY"], x0, y0, x1, y1))
    return library


def run(design: str, out_dir: Path, moves: int = 4000, passes: int = 4) -> dict:
    spec = DESIGNS[design]
    out_dir = out_dir if out_dir.is_absolute() else (ROOT / out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    build_dir = out_dir / "netlist"

    print(f"== {design}: synthesis")
    json_netlist = synthesise(design, build_dir)
    netlist = map_netlist(json_netlist, spec["top"])
    print(f"   {netlist.stats()['instances']} instances, {netlist.stats()['nets']} nets, "
          f"{netlist.stats()['cell_area_um2']} um^2 of cells")

    print(f"== {design}: placement")
    placement = place(netlist, moves=moves)
    print(f"   {placement.rows} rows, core {placement.core_width:.1f} x "
          f"{placement.core_height:.1f} um, utilisation {placement.utilisation:.1%}, "
          f"HPWL {placement.hpwl_before:.0f} -> {placement.hpwl_after:.0f} um")

    print(f"== {design}: routing")
    grid = Grid(netlist)
    route_result, geometry = route(netlist, grid=grid, passes=passes)
    total_nets = len([n for n in netlist.nets.values() if len(n.pins) > 1 or n.is_port])
    completion = route_result.routed / total_nets if total_nets else 1.0
    print(f"   {route_result.routed}/{total_nets} nets routed "
          f"({completion:.1%}), {route_result.wire_length_um:.0f} um of wire, "
          f"{route_result.vias} vias")
    if route_result.failed:
        print(f"   unrouted: {', '.join(route_result.failed[:6])}"
              + (" ..." if len(route_result.failed) > 6 else ""))

    print(f"== {design}: layout + GDS")
    layout = build_layout(netlist, geometry, grid=grid)
    max_x = max((inst.x + LIBRARY[inst.cell].width) for inst in netlist.instances.values())
    max_y = max(inst.y + RULES.cell_height for inst in netlist.instances.values())
    layout.bounds = (-1.0, -1.0, max_x + 1.0, max_y + 1.0)
    library = build_gds_library(netlist, layout)
    gds_path = gdsii.write_gds(out_dir / f"{design}.gds", library)
    gds_summary = gdsii.read_gds_summary(gds_path)
    print(f"   {gds_path.name}: {gds_summary['bytes']} bytes, "
          f"{len(gds_summary['structures'])} structures")

    print(f"== {design}: DRC")
    drc = check_drc(layout)
    print(f"   {drc.checks} checks, {len(drc.violations)} violations")

    print(f"== {design}: connectivity (LVS-lite)")
    lvs = check_connectivity(layout, netlist)
    print(f"   {lvs.connected_nets} nets connected, {len(lvs.open_nets)} open, "
          f"{len(lvs.shorts)} shorted")

    print(f"== {design}: timing")
    timing = analyse_timing(netlist, geometry, spec["clock_period_ns"])
    print(f"   critical path {timing.critical_path_ns:.3f} ns, "
          f"slack {timing.slack_ns:+.3f} ns, Fmax {timing.fmax_mhz:.0f} MHz")

    report = {
        "design": design,
        "top": spec["top"],
        "technology": library_summary()["technology"],
        "clock_period_ns": spec["clock_period_ns"],
        "netlist": netlist.stats(),
        "placement": asdict(placement),
        "routing": {**route_result.to_dict(),
                    "completion": round(completion, 4),
                    "total_nets": total_nets},
        "gds": {"path": str(gds_path.relative_to(ROOT)), **gds_summary},
        "drc": drc.to_dict(),
        "connectivity": lvs.to_dict(),
        "timing": timing.to_dict(),
        "flow_status": _status(completion, drc, lvs, timing),
    }
    (out_dir / f"{design}.json").write_text(json.dumps(report, indent=2))
    (out_dir / f"{design}_report.md").write_text(render_report(report))
    print(f"== {design}: {report['flow_status']}")
    return report


def _status(completion: float, drc, lvs, timing) -> str:
    if completion >= 1.0 and drc.status == "clean" and lvs.status == "clean" and timing.status == "met":
        return "PASS (fully routed, DRC clean, connectivity clean, timing met)"
    issues = []
    if completion < 1.0:
        issues.append(f"routing {completion:.1%}")
    if drc.status != "clean":
        issues.append(f"DRC {drc.status}: {len(drc.violations)} violations")
    if lvs.status != "clean":
        issues.append(f"connectivity {lvs.status}: {len(lvs.open_nets)} open, {len(lvs.shorts)} short")
    if timing.status != "met":
        issues.append(f"timing {timing.status}")
    return "INCOMPLETE (" + "; ".join(issues) + ")"


def render_report(report: dict) -> str:
    r = report
    lines = [
        f"# {r['design']} - RTL-to-GDSII report",
        "",
        f"* technology: `{r['technology']}`",
        f"* clock target: **{r['clock_period_ns']} ns**",
        f"* flow status: **{r['flow_status']}**",
        "",
        "## Netlist",
        "",
        f"| instances | nets | cell area |",
        f"| ---: | ---: | ---: |",
        f"| {r['netlist']['instances']} | {r['netlist']['nets']} | "
        f"{r['netlist']['cell_area_um2']} um^2 |",
        "",
        "Cell histogram: "
        + ", ".join(f"`{k}` x{v}" for k, v in r["netlist"]["cell_histogram"].items()),
        "",
        "## Placement",
        "",
        f"* rows: {r['placement']['rows']}, core "
        f"{r['placement']['core_width']:.1f} x {r['placement']['core_height']:.1f} um",
        f"* utilisation: {r['placement']['utilisation']:.1%}",
        f"* HPWL: {r['placement']['hpwl_before']:.1f} -> "
        f"{r['placement']['hpwl_after']:.1f} um "
        f"({(1 - r['placement']['hpwl_after'] / max(r['placement']['hpwl_before'], 1e-9)):.1%} shorter)",
        "",
        "## Routing",
        "",
        f"* nets routed: {r['routing']['nets_routed']} / {r['routing']['total_nets']} "
        f"({r['routing']['completion']:.1%})",
        f"* wire length: {r['routing']['wire_length_um']} um, vias: {r['routing']['vias']}",
        f"* layer usage: {r['routing'].get('layer_usage_um', {})}",
    ]
    if r["routing"]["nets_failed"]:
        lines += ["", "**Unrouted nets** (reported, not hidden): "
                  + ", ".join(f"`{n}`" for n in r["routing"]["nets_failed"][:20])]
    lines += [
        "",
        "## GDS",
        "",
        f"* file: `{r['gds']['path']}` ({r['gds']['bytes']} bytes)",
        f"* structures: {len(r['gds']['structures'])}",
        f"* units: {r['gds']['units']}",
        "",
        "## Sign-off",
        "",
        f"| check | status | detail |",
        f"| --- | --- | --- |",
        f"| DRC | {r['drc']['status']} | {r['drc']['checks']} checks, "
        f"{r['drc']['violations']} violations |",
        f"| Connectivity (LVS-lite) | {r['connectivity']['status']} | "
        f"{r['connectivity']['connected_nets']} nets connected, "
        f"{len(r['connectivity']['open_nets'])} opens, "
        f"{len(r['connectivity']['shorts'])} shorts |",
        f"| Timing | {r['timing']['status']} | critical path "
        f"{r['timing']['critical_path_ns']:.3f} ns, slack {r['timing']['slack_ns']:+.3f} ns, "
        f"Fmax {r['timing']['fmax_mhz']:.0f} MHz |",
        "",
        "### Scope of the checks",
        "",
        "* DRC covers width, spacing and via enclosure for the layers this flow",
        "  draws.  Antenna, density and latch-up rules are not implemented.",
        "* Connectivity is extracted from the layout and compared net by net with",
        "  the netlist.  It is *not* transistor-level LVS: a cell whose schematic",
        "  and layout disagree would not be caught here.",
        "* Timing uses library intrinsic delays and an Elmore wire model.  There",
        "  is no clock tree, no crosstalk and no derating, so the number is a",
        "  sanity check on the router, not a sign-off timer.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", default="crc16_ccitt", choices=sorted(DESIGNS))
    parser.add_argument("--out", default="asic/build")
    parser.add_argument("--moves", type=int, default=4000, help="placement anneal moves")
    parser.add_argument("--passes", type=int, default=4, help="routing retry passes")
    parser.add_argument("--all", action="store_true", help="run every design")
    args = parser.parse_args(argv)

    designs = sorted(DESIGNS) if args.all else [args.design]
    reports = []
    for design in designs:
        reports.append(run(design, Path(args.out), moves=args.moves, passes=args.passes))
    summary = {
        "designs": {r["design"]: {"status": r["flow_status"],
                                  "routing_completion": r["routing"]["completion"],
                                  "drc": r["drc"]["status"],
                                  "connectivity": r["connectivity"]["status"],
                                  "timing": r["timing"]["status"]} for r in reports},
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
