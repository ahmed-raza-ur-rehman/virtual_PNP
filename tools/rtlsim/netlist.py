"""Reader for the Yosys JSON netlist format.

Only the pieces the simulator needs are modelled: module parameters, cell
types and connections, and the public net names.  The cell set is intentionally
narrow - it is whatever ``synth`` + ``abc`` produces for the blocks in ``rtl/``
- and anything outside it raises :class:`NetlistError` instead of being
silently ignored, because a simulator that skips cells is worse than no
simulator at all.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


class NetlistError(RuntimeError):
    """Raised when a netlist cannot be loaded or contains unknown constructs."""


@dataclass
class Cell:
    name: str
    type: str
    connections: dict[str, list[int | str]]
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass
class Design:
    """A flattened, single-module design ready to simulate."""

    name: str
    cells: dict[str, Cell]
    ports: dict[str, dict]  # name -> {"direction": str, "bits": [int]}
    netnames: dict[str, dict]  # name -> {"bits": [int], "hide_name": int}
    top: str

    @property
    def port_order(self) -> list[str]:
        return list(self.ports)

    def cell_types(self) -> dict[str, int]:
        hist: dict[str, int] = {}
        for cell in self.cells.values():
            hist[cell.type] = hist.get(cell.type, 0) + 1
        return hist


def load_design(json_path: str | Path, top: str | None = None) -> Design:
    """Load a Yosys JSON netlist.

    :param top: module to simulate; defaults to the design's ``top`` attribute
        or, failing that, the only module in the file.
    """
    path = Path(json_path)
    if not path.exists():
        raise NetlistError(f"netlist not found: {path}; run `make hdl-synth` first")
    data = json.loads(path.read_text())
    modules: dict[str, dict] = data.get("modules", {})
    if not modules:
        raise NetlistError(f"{path} contains no modules")
    if top is None:
        top = data.get("top") or (next(iter(modules)) if len(modules) == 1 else None)
    if top is None:
        raise NetlistError(f"{path} has several modules; pass --top explicitly")
    if top not in modules:
        raise NetlistError(f"module {top!r} not in {path} (found {sorted(modules)})")
    mod = modules[top]
    if len(modules) > 1:
        submodules = [m["type"] for m in mod.get("cells", {}).values() if m["type"] in modules]
        if submodules:
            raise NetlistError(
                f"{top} still instantiates submodules {sorted(set(submodules))}; "
                "synthesise with -flatten before simulating"
            )

    # metadata cells carry no logic (scope information for debuggers) and are
    # dropped here so that the simulator never has to know about them
    metadata = {"$scopeinfo", "$specify2", "$specify3", "$specrule"}

    cells = {
        name: Cell(
            name=name,
            type=raw["type"],
            connections=raw.get("connections", {}),
            parameters={k: v for k, v in raw.get("parameters", {}).items()},
        )
        for name, raw in mod.get("cells", {}).items()
        if raw["type"] not in metadata
    }
    return Design(
        name=top,
        cells=cells,
        ports=mod.get("ports", {}),
        netnames=mod.get("netnames", {}),
        top=top,
    )
