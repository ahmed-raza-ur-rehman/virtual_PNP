"""Netlist in, standard-cell netlist out.

Reads the yosys JSON netlist (the same artefact the RTL simulator and the
synthesis reports use), resolves the bits of every cell connection into named
nets and maps each gate onto a library cell.  The result is a :class:`Netlist`
of :class:`Instance` objects and :class:`Net` objects that the placer, router
and sign-off checks all consume.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .tech import LIBRARY, YOSYS_MAP


class MapError(RuntimeError):
    """Raised when the netlist cannot be mapped onto the library."""


@dataclass
class Instance:
    name: str
    cell: str                      # library cell name
    pins: dict[str, str]           # library pin -> net name
    x: float = 0.0                 # placement (lower-left corner), um
    y: float = 0.0
    row: int = 0
    extra_cells: list[str] = field(default_factory=list)   # added inverters etc.


@dataclass
class Net:
    name: str
    pins: list[tuple[str, str]] = field(default_factory=list)   # (instance, pin)
    is_port: bool = False
    driver: tuple[str, str] | None = None
    route: list[tuple[float, float, int]] = field(default_factory=list)
    #: (instance, pin) -> routing node the router actually connected to
    pin_nodes: dict[tuple[str, str], tuple[int, int, int]] = field(default_factory=dict)


@dataclass
class Netlist:
    top: str
    instances: dict[str, Instance] = field(default_factory=dict)
    nets: dict[str, Net] = field(default_factory=dict)
    ports: dict[str, dict] = field(default_factory=dict)

    @property
    def area_um2(self) -> float:
        return sum(LIBRARY[i.cell].area_um2 for i in self.instances.values()
                   if i.cell in LIBRARY)

    def stats(self) -> dict:
        hist: dict[str, int] = {}
        for inst in self.instances.values():
            hist[inst.cell] = hist.get(inst.cell, 0) + 1
        return {
            "instances": len(self.instances),
            "nets": len(self.nets),
            "cell_histogram": dict(sorted(hist.items())),
            "cell_area_um2": round(self.area_um2, 2),
        }


def _bit_name(design_bits: dict[int, str], bit) -> str:
    if isinstance(bit, int):
        return design_bits.get(bit, f"bit{bit}")
    return {"1": "$true", "0": "$false", "x": "$undef", "z": "$undef"}.get(bit, f"const{bit}")


def map_netlist(json_path: str | Path, top: str) -> Netlist:
    import json

    path = Path(json_path)
    data = json.loads(path.read_text())
    if top not in data["modules"]:
        raise MapError(f"module {top} not found in {path}")
    module = data["modules"][top]

    # bit -> canonical net name.
    #
    # A yosys "netname" describes a *vector*: all of its bits share one name
    # string.  Collapsing those bits onto a single net (the first version of
    # this reader did) makes independent bits look electrically joined and
    # produces bogus multiple-driver errors.  Vector names are therefore
    # expanded per bit, with the LSB - bit 0 of the yosys bit list - first.
    def expand(name: str, bits: list) -> dict[int, str]:
        clean = name.lstrip("\\")
        int_bits = [b for b in bits if isinstance(b, int)]
        if len(int_bits) <= 1:
            return {int_bits[0]: clean} if int_bits else {}
        return {b: f"{clean}[{i}]" for i, b in enumerate(int_bits)}

    bit_to_name: dict[int, str] = {}
    for name, port in module.get("ports", {}).items():
        bit_to_name.update(expand(name, port["bits"]))
    for name, net in module.get("netnames", {}).items():
        for bit, net_name in expand(name, net["bits"]).items():
            bit_to_name.setdefault(bit, net_name)

    netlist = Netlist(top=top, ports=module.get("ports", {}))

    def net_of(bit) -> str:
        return _bit_name(bit_to_name, bit)

    for cell_name, cell in module.get("cells", {}).items():
        ctype = cell["type"]
        if ctype not in YOSYS_MAP:
            raise MapError(
                f"{cell_name}: no library cell for {ctype}. "
                "Add it to YOSYS_MAP in asic/miniflow/tech.py and re-run."
            )
        lib_cell = YOSYS_MAP[ctype]
        connections = cell.get("connections", {})

        def port_net(*candidates: str) -> str | None:
            for candidate in candidates:
                if candidate in connections:
                    bits = [b for b in connections[candidate] if isinstance(b, int)]
                    if not bits:
                        continue
                    # multi-bit pins are joined for connectivity purposes; the
                    # library cells in this flow are single-bit by construction
                    return net_of(bits[0])
            return None

        pins: dict[str, str] = {}
        if lib_cell in {"INV_X1", "BUF_X1"}:
            pins["A"] = port_net("A") or "$undef"
            pins["Y"] = port_net("Y") or "$undef"
        elif LIBRARY[lib_cell].function in {"nand2", "nor2", "and2", "or2", "xor2", "xnor2", "andnot"}:
            pins["A"] = port_net("A") or "$undef"
            pins["B"] = port_net("B") or "$undef"
            pins["Y"] = port_net("Y") or "$undef"
        elif LIBRARY[lib_cell].function == "mux2":
            pins["A"] = port_net("A") or "$undef"
            pins["B"] = port_net("B") or "$undef"
            pins["S"] = port_net("S") or "$undef"
            pins["Y"] = port_net("Y") or "$undef"
        elif LIBRARY[lib_cell].function == "dff":
            pins["D"] = port_net("D") or "$undef"
            pins["CLK"] = port_net("C", "CLK") or "$undef"
            pins["Q"] = port_net("Q") or "$undef"
        elif LIBRARY[lib_cell].function in {"tie1", "tie0"}:
            pins["Y"] = port_net("Y") or "$undef"

        inst = Instance(name=cell_name.lstrip("\\"), cell=lib_cell, pins=pins)
        netlist.instances[inst.name] = inst

        for pin, net in pins.items():
            n = netlist.nets.setdefault(net, Net(name=net))
            n.pins.append((inst.name, pin))
            if pin == "Y" or pin == "Q":
                if n.driver is not None:
                    # multiple drivers only happen for tri-state, which this
                    # technology model does not support
                    raise MapError(f"net {net} has two drivers: {n.driver} and {(inst.name, pin)}")
                n.driver = (inst.name, pin)

    for name, port in module.get("ports", {}).items():
        for b in port["bits"]:
            if isinstance(b, int):
                net = net_of(b)
                n = netlist.nets.setdefault(net, Net(name=net))
                n.is_port = True

    return netlist
