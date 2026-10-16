"""Row-based standard-cell placement.

Stages
------
1. *row assignment*: cells are ordered by a connectivity-driven traversal, then
   packed left to right into rows whose width is the square root of the total
   cell area (the classical aspect-ratio estimate).  Clock and reset nets are
   ordered first because they fan out everywhere.
2. *legalisation*: rows are padded so every cell sits on the routing grid.
3. *improvement*: simulated annealing over pairwise swaps, minimising
   half-perimeter wire length (HPWL) of the estimated net boxes, with a fixed
   number of moves so that runtime is bounded and reproducible.

The annealer reuses :mod:`pnp.optimization.advanced`, so the placement engine
and the machine's placement-order engine share one implementation of the
algorithm - and one set of tests.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .netlist_map import Netlist
from .tech import CHANNEL_PITCHES, LIBRARY, RULES


class PlacementError(RuntimeError):
    """Raised when legalisation leaves overlapping cells."""


@dataclass
class PlacementResult:
    rows: int
    row_width: float
    core_width: float
    core_height: float
    hpwl_before: float
    hpwl_after: float
    utilisation: float


def pin_position(netlist: Netlist, inst_name: str, pin: str) -> tuple[float, float]:
    inst = netlist.instances[inst_name]
    cell = LIBRARY[inst.cell]
    px, py = cell.pins[pin]
    return inst.x + px, inst.y + py


def hpwl(netlist: Netlist) -> float:
    """Half-perimeter wire length over all multi-pin nets, in micrometres."""
    total = 0.0
    for net in netlist.nets.values():
        if net.is_port and len(net.pins) <= 1:
            continue
        xs, ys = [], []
        for inst_name, pin in net.pins:
            if pin in ("Y", "Q"):
                continue                      # count each box from its sinks
            x, y = pin_position(netlist, inst_name, pin)
            xs.append(x)
            ys.append(y)
        if len(xs) < 2:
            continue
        total += (max(xs) - min(xs)) + (max(ys) - min(ys))
    return total


def _connectivity_order(netlist: Netlist) -> list[str]:
    """Order cells so that neighbours in the list are electrically close."""
    adjacency: dict[str, set[str]] = {name: set() for name in netlist.instances}
    for net in netlist.nets.values():
        members = [name for name, _ in net.pins]
        for a in members:
            adjacency[a].update(m for m in members if m != a)

    # seed with the highest-degree cell (usually a clock buffer or a wide gate)
    remaining = set(netlist.instances)
    order: list[str] = []
    while remaining:
        seed = max(remaining, key=lambda n: (len(adjacency[n]), n))
        queue = [seed]
        while queue:
            current = queue.pop(0)
            if current not in remaining:
                continue
            order.append(current)
            remaining.discard(current)
            neighbours = sorted(adjacency[current] & remaining,
                                key=lambda n: -len(adjacency[n]))
            queue.extend(neighbours)
    return order


def place(netlist: Netlist, moves: int = 4000, seed: int = 7) -> PlacementResult:
    """Place every instance; the netlist is mutated in place."""
    total_area = netlist.area_um2
    if not netlist.instances:
        return PlacementResult(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    row_width = max(20.0, math.sqrt(total_area * 2.0))
    pitch = RULES.routing_pitch
    # Rows are separated by a routing channel: real standard-cell rows abut and
    # route over the cells on upper metals, but this technology model has only
    # M1/M2, so the horizontal tracks have to live in explicit channels.
    row_pitch = RULES.cell_height + CHANNEL_PITCHES * pitch
    order = _connectivity_order(netlist)

    # ---- stage 1: row packing -------------------------------------------
    row, x = 0, 0.0
    for name in order:
        inst = netlist.instances[name]
        width = LIBRARY[inst.cell].width
        if x + width > row_width and x > 0:
            row += 1
            x = 0.0
        # Positions stay on the routing grid by construction: cell widths are
        # whole pitches and the cursor advances by whole pitches, so no
        # rounding is applied here (rounding to the nearest grid point can move
        # a cell backwards on top of its neighbour).
        inst.row = row
        inst.x = round(x, 4)
        inst.y = round(row * row_pitch / pitch) * pitch
        x = inst.x + width + pitch
    rows = row + 1
    core_width = max(
        (inst.x + LIBRARY[inst.cell].width) for inst in netlist.instances.values()
    )
    core_height = (rows - 1) * row_pitch + RULES.cell_height

    before = hpwl(netlist)

    # ---- stage 2: annealing over legal row rotations --------------------
    #
    # The move is a rotation of a contiguous run of cells inside one row.  It
    # preserves the run's total width, so the placement stays legal by
    # construction - no legaliser is required, and no accepted move can
    # introduce an overlap.  An earlier version swapped the x coordinates of
    # two arbitrary cells, which moved cells out of their row packing and
    # produced 25 overlapping pairs that the legality check then rejected.
    rng = random.Random(seed)
    rows_cells: dict[int, list[str]] = {}
    for name, inst in netlist.instances.items():
        rows_cells.setdefault(inst.row, []).append(name)
    for row_index, names_in_row in rows_cells.items():
        names_in_row.sort(key=lambda n: netlist.instances[n].x)

    def relayout(row_index: int) -> None:
        cursor = 0.0
        for name in rows_cells[row_index]:
            inst = netlist.instances[name]
            inst.x = round(cursor, 4)
            cursor += LIBRARY[inst.cell].width + pitch

    current = hpwl(netlist)
    temperature = max(1.0, current * 0.02)
    candidate_rows = [r for r, names_in_row in rows_cells.items() if len(names_in_row) >= 3]
    if candidate_rows:
        for _ in range(moves):
            row_index = rng.choice(candidate_rows)
            names_in_row = rows_cells[row_index]
            i = rng.randrange(0, len(names_in_row) - 1)
            j = rng.randrange(i + 1, len(names_in_row))
            segment = names_in_row[i:j + 1]
            names_in_row[i:j + 1] = segment[-1:] + segment[:-1]     # rotate right
            relayout(row_index)
            candidate = hpwl(netlist)
            delta = candidate - current
            if delta <= 0 or rng.random() < math.exp(-delta / max(temperature, 1e-9)):
                current = candidate
            else:
                names_in_row[i:j + 1] = segment                         # revert
                relayout(row_index)
            temperature *= 0.9995
            if temperature < 1e-3:
                break

    after = hpwl(netlist)
    used_area = total_area
    core_area = core_width * core_height
    return PlacementResult(
        rows=rows,
        row_width=row_width,
        core_width=core_width,
        core_height=core_height,
        hpwl_before=round(before, 2),
        hpwl_after=round(after, 2),
        utilisation=round(used_area / core_area, 4) if core_area else 0.0,
    )
