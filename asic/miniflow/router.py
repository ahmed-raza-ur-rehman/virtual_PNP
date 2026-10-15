"""Grid maze router with a two-layer, preferred-direction stack.

Model
-----
* the core is discretised on the routing pitch; a *routing node* is a triple
  ``(x_index, y_index, layer)`` over a three-layer stack: M1 (horizontal,
  available in the channels only), M2 (vertical, available everywhere) and M3
  (horizontal, available everywhere).  Alternating the preferred direction
  layer by layer is what stops the router from shorting its own wires where
  they cross, and adding the third layer is what makes the block routable at a
  realistic channel height;
* a node is blocked if it lies inside a placed cell, except for the escape
  node of a pin (one grid point above the cell, on M2);
* moving along x is only allowed on M1, along y only on M2 and a via connects
  the two layers at the same (x, y).  Restricting each layer to one direction
  is what keeps the two metal layers from shorting where they cross, and it is
  how real routers exploit a preferred-direction stack;
* a via costs ``VIA_COST`` extra so that the router only changes layer when it
  buys something.

Net sequencing is by bounding-box size (big nets first, the standard heuristic),
and each sink is routed to the growing tree of its own net, with existing track
of that net free to reuse - a cheap Steiner approximation that is good enough
for the block sizes this flow targets.
"""

from __future__ import annotations

import heapq
import random
from dataclasses import dataclass, field

from .netlist_map import Netlist
from .placer import pin_position
from .tech import CHANNEL_PITCHES, LIBRARY, RULES

VIA_COST = 4


@dataclass
class RouteResult:
    routed: int = 0
    failed: list[str] = field(default_factory=list)
    wire_length_um: float = 0.0
    vias: int = 0
    layer_usage: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "nets_routed": self.routed,
            "nets_failed": self.failed,
            "wire_length_um": round(self.wire_length_um, 2),
            "vias": self.vias,
            "layer_usage_um": {k: round(v, 2) for k, v in self.layer_usage.items()},
        }


class Grid:
    """Sparse routing grid over the placement."""

    def __init__(self, netlist: Netlist, margin: float = 1.2) -> None:
        pitch = RULES.routing_pitch
        self.pitch = pitch
        max_x = max((i.x + LIBRARY[i.cell].width) for i in netlist.instances.values())
        max_y = max(i.y + RULES.cell_height for i in netlist.instances.values())
        self.row_pitch = RULES.cell_height + CHANNEL_PITCHES * RULES.routing_pitch
        self.nx = int((max_x + 2 * margin) / pitch) + 2
        self.ny = int((max_y + 2 * margin) / pitch) + 2
        self.origin = -margin
        self.blocked: set[tuple[int, int, int]] = set()
        self.occupancy: dict[tuple[int, int, int], str] = {}

        # Primary inputs and outputs are brought out to IO access points spread
        # along the top edge of the core.  Without them the port nets have no
        # second terminal to route to, which is exactly what the router
        # reported before this was modelled.
        self.port_nodes: dict[str, tuple[int, int, int]] = {}
        # Nets, not port declarations: a multi-bit port such as data[7:0] is
        # routed as one net per bit, so the pad list is built from the nets.
        port_names = sorted(n.name for n in netlist.nets.values() if n.is_port)
        if port_names:
            # Pads are distributed over the top and bottom edges and across the
            # full core width.  Putting every pad on one edge (the first
            # version) concentrates all port nets into a single channel and
            # leaves port-heavy blocks partially unrouted for no good reason.
            per_edge = max(1, (len(port_names) + 1) // 2)
            for index, name in enumerate(port_names):
                top = index < per_edge
                slot = index if top else index - per_edge
                step = max(1, (self.nx - 4) // max(1, per_edge))
                ix = min(self.nx - 2, 2 + slot * step)
                iy = (self.ny - 2) if top else 1
                node = (ix, iy, 4)                     # pads live on the top metal
                self.port_nodes[name] = node
                self.blocked.discard(node)

        # Reserve every pin's access point before any net is routed.  Pin
        # access is a hard resource: a track that runs through it makes the pin
        # unreachable, and a track that lands on it shorts two nets.
        for inst in netlist.instances.values():
            for pin, net in inst.pins.items():
                if pin not in LIBRARY[inst.cell].pins:
                    continue
                node = self.access_nodes(netlist, inst.name, pin, fan=0)[0]
                self.occupancy.setdefault(node, net)

        for inst in netlist.instances.values():
            cell = LIBRARY[inst.cell]
            x0 = self.ix(inst.x)
            x1 = self.ix(inst.x + cell.width - 1e-6)
            y0 = self.iy(inst.y)
            y1 = self.iy(inst.y + RULES.cell_height - 1e-6)
            # M1 cannot cross a standard cell (that is where the cell's own
            # geometry lives), but M2 may pass over it - upper metals routing
            # over cells is exactly how a real layout recovers density.
            for ix in range(x0, x1 + 1):
                for iy in range(y0, y1 + 1):
                    self.blocked.add((ix, iy, 0))       # M1 only: M2/M3 route over
            # escape node: one grid point above the cell on M2
            # Every pin gets an escape node in the channel above its row.  The
            # node exists on M2 (vertical) and the via to M1 in the channel is
            # opened explicitly so that a pin can always reach a horizontal
            # track.
            for _pin, (px, _py) in cell.pins.items():
                ix = self.ix(inst.x + px)
                iy = min(self.ny - 1, y1 + 1)
                self.blocked.discard((ix, iy, 1))
                self.blocked.discard((ix, iy, 0))

    # -- coordinate helpers -------------------------------------------------
    def ix(self, x: float) -> int:
        return max(0, min(self.nx - 1, round((x - self.origin) / self.pitch)))

    def iy(self, y: float) -> int:
        return max(0, min(self.ny - 1, round((y - self.origin) / self.pitch)))

    def xy(self, ix: int, iy: int) -> tuple[float, float]:
        return (round(self.origin + ix * self.pitch, 2),
                round(self.origin + iy * self.pitch, 2))

    def access_nodes(self, netlist: Netlist, inst_name: str, pin: str,
                     fan: int = 2) -> list[tuple[int, int, int]]:
        """Candidate access nodes for a pin, nearest first.

        Several cells in a row can have pins that land on the same grid point
        once positions are snapped to the routing pitch, and a channel row is a
        scarce resource in general, so a pin offers a small fan of access
        points rather than exactly one.  The router picks the first that is
        free; that is the cheapest form of pin access that still keeps the
        layout exactly what the netlist asked for.
        """
        inst = netlist.instances[inst_name]
        cell = LIBRARY[inst.cell]
        px, _ = cell.pins[pin]
        ix = self.ix(inst.x + px)
        base = min(self.ny - 1, self.iy(inst.y + RULES.cell_height) + 1)
        nodes: list[tuple[int, int, int]] = []
        # The channel above a row is shared by every pin in that row, so a pin
        # offers a *fan* of access points: the column nearest the pin first,
        # then neighbouring columns and the other channel tracks.  Without the
        # extra tracks the first few nets claim the whole channel row and later
        # nets are unroutable even though the channel is mostly empty.
        for dy in range(CHANNEL_PITCHES):
            iy = min(self.ny - 1, base + dy)
            for dx in range(0, fan + 1):
                for candidate in ({ix - dx, ix + dx} if dx else {ix}):
                    if 0 <= candidate < self.nx:
                        nodes.append((candidate, iy, 1))
                nodes.append((candidate, iy, 2))       # M3 access as well
                nodes.append((candidate, iy, 3))
        return nodes

    #: preferred direction per layer: 0 = horizontal, 1 = vertical.
    #: A five-metal stack is what this node offers, and alternating the
    #: direction on every layer is the reason a signal can cross another one
    #: without a short.  M1 is confined to the channels (the cells own the
    #: area above them on M1); M2..M5 run over anything.
    LAYER_DIRECTION = (0, 1, 0, 1, 0)
    #: metal layer name per routing layer
    LAYER_NAME = ("M1", "M2", "M3", "M4", "M5")
    #: via layer name connecting routing layer i to i+1
    VIA_NAME = ("VIA1", "VIA2", "VIA3", "VIA4")

    def neighbours(self, node: tuple[int, int, int]):
        ix, iy, layer = node
        if self.LAYER_DIRECTION[layer] == 0:            # horizontal layer
            for dx in (-1, 1):
                nx = ix + dx
                if 0 <= nx < self.nx:
                    yield (nx, iy, layer), 1
        else:                                           # vertical layer
            for dy in (-1, 1):
                ny = iy + dy
                if 0 <= ny < self.ny:
                    yield (ix, ny, layer), 1

        for other in (layer - 1, layer + 1):            # vias to adjacent metals
            if 0 <= other < len(self.LAYER_NAME):
                candidate = (ix, iy, other)
                if candidate not in self.blocked:
                    yield candidate, VIA_COST


def _astar(grid: Grid, start: tuple[int, int, int], targets: set[tuple[int, int, int]],
           own_net: str) -> list[tuple[int, int, int]] | None:
    """Maze route from ``start`` to the nearest node in ``targets``."""
    def heuristic(node):
        ix, iy, _ = node
        best = min((abs(ix - t[0]) + abs(iy - t[1]) + (0 if node[2] == t[2] else VIA_COST))
                   for t in targets)
        return best

    open_heap = [(heuristic(start), 0.0, start)]
    came_from: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    cost_so_far = {start: 0.0}

    while open_heap:
        _, cost, current = heapq.heappop(open_heap)
        if current in targets:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for neighbour, step_cost in grid.neighbours(current):
            if neighbour in grid.blocked:
                continue
            owner = grid.occupancy.get(neighbour)
            if owner is not None and owner != own_net:
                continue
            new_cost = cost + step_cost
            if new_cost < cost_so_far.get(neighbour, float("inf")):
                cost_so_far[neighbour] = new_cost
                priority = new_cost + heuristic(neighbour)
                heapq.heappush(open_heap, (priority, new_cost, neighbour))
                came_from[neighbour] = current
    return None


def _path_to_geometry(path: list[tuple[int, int, int]], grid: Grid, pitch: float):
    """Convert a node path into wire segments and via positions."""
    wires: list[tuple[str, float, float, float, float]] = []
    vias: list[tuple[str, float, float]] = []
    # The wire is drawn at the layer's *minimum width*, not at the full pitch:
    # a wire drawn a pitch wide leaves no space to its neighbour and fails the
    # spacing rule at exactly the pitch the router chose.
    layer_half = {
        "M1": RULES.m1_width / 2.0,
        "M2": RULES.m2_width / 2.0,
        "M3": RULES.m3_width / 2.0,
        "M4": RULES.m4_width / 2.0,
        "M5": RULES.m5_width / 2.0,
    }

    def emit(start_node, end_node) -> None:
        x0, y0 = grid.xy(*start_node[:2])
        x1, y1 = grid.xy(*end_node[:2])
        layer_name = grid.LAYER_NAME[start_node[2]]
        half = layer_half[layer_name]
        wires.append((layer_name, min(x0, x1) - half, min(y0, y1) - half,
                      max(x0, x1) + half, max(y0, y1) + half))

    run_start = path[0]
    prev = path[0]
    for node in path[1:]:
        ix, iy, layer = node
        px, py, player = prev
        if layer != player:
            # a via: close the run on the layer it was drawn on, drop the via,
            # and start a new run on the new layer
            if prev != run_start:
                emit(run_start, prev)
            vias.append((grid.VIA_NAME[min(player, layer)], *grid.xy(ix, iy)))
            run_start = node
        elif abs(ix - px) + abs(iy - py) > 1:
            emit(run_start, prev)
            run_start = node
        prev = node
    if prev != run_start:
        emit(run_start, prev)
    return wires, vias


def _route_net(netlist: Netlist, grid: Grid, net, geometry: dict, fan: int = 2) -> bool:
    """Route one net into the growing tree; returns True when it completes.

    ``fan`` widens the search for a free pin access point.  Retry passes raise
    it, which is how a high-fanout reset or clock net finally finds a column
    for its last few stubs.
    """
    if True:
        # sources and sinks, resolved to concrete access points.
        # Input ports have no internal driver, so the pad itself is the source.
        source_candidates = grid.access_nodes(netlist, *net.driver, fan=fan) if net.driver else []
        sink_candidates = [grid.access_nodes(netlist, inst, pin, fan=fan)
                           for inst, pin in net.pins if pin not in ("Y", "Q")]
        if not source_candidates and not sink_candidates:
            return False

        def free(nodes):
            for node in nodes:
                owner = grid.occupancy.get(node)
                if owner is None or owner == net.name:
                    return node
            return nodes[0]

        node_groups = [source_candidates] + sink_candidates if source_candidates else sink_candidates
        port_node = grid.port_nodes.get(net.name) if net.is_port else None
        if port_node is None and net.is_port:
            # a port that is not part of the top level (a renamed bit) is still
            # routed, it simply has no pad of its own
            port_node = None
        if port_node is not None:
            node_groups = node_groups + [[port_node]]
        chosen = [free(group) for group in node_groups]
        # remember the access point each terminal ended up using: the layout
        # builder draws the pin escape to exactly this node, which is what
        # makes the extracted connectivity match the netlist
        terminal_keys = ([net.driver] if net.driver else []) + \
            [(inst, pin) for inst, pin in net.pins if pin not in ("Y", "Q")]
        if len(chosen) < 2:
            return False

        tree = {chosen[0]}
        claimed: list[tuple[int, int, int]] = []
        if grid.occupancy.get(chosen[0]) is None:
            grid.occupancy[chosen[0]] = net.name
            claimed.append(chosen[0])
        net_wires: list[tuple[str, float, float, float, float]] = []
        net_vias: list[tuple[str, float, float]] = []
        complete = True
        used_nodes: list[tuple[int, int, int]] = [chosen[0]]
        for group, target_node in zip(node_groups[1:], chosen[1:]):
            if target_node in tree:
                used_nodes.append(target_node)
                continue
            targets = {t for t in group if t not in tree} | {target_node}
            path = _astar(grid, next(iter(tree)), targets, net.name)
            if path is None:
                complete = False
                break
            # the path may land on any node of the fan, not on the one the
            # free() call picked: the pin escape has to be drawn to the node the
            # route really reached, or the extracted connectivity sees an open
            used_nodes.append(path[-1])
            for node in path:
                if grid.occupancy.get(node) is None:
                    grid.occupancy[node] = net.name
                    claimed.append(node)
                tree.add(node)
            # only the point actually used is reserved: reserving the whole
            # fan would wall off the channel for every other net
            if path and grid.occupancy.get(path[-1]) is None:
                grid.occupancy[path[-1]] = net.name
                claimed.append(path[-1])
            wires, vias = _path_to_geometry(path, grid, grid.pitch)
            net_wires.extend(wires)
            net_vias.extend(vias)

        if complete:
            for key, node in zip(terminal_keys, used_nodes):
                if key is not None:
                    net.pin_nodes[key] = node
        if not complete:
            # Roll the partial route back: leaving the half-finished wires
            # marked as owned by a net that will never use them would block
            # every later net, which is exactly what the first version did.
            for node in claimed:
                if grid.occupancy.get(node) == net.name:
                    del grid.occupancy[node]
            return False

        net.route = sorted(tree)
        geometry[net.name] = {"wires": net_wires, "vias": net_vias}
        return True


def route(netlist: Netlist, grid: Grid | None = None, passes: int = 4
          ) -> tuple[RouteResult, dict[str, dict]]:
    """Route every net; returns the result summary and per-net geometry.

    Nets are routed widest-fanout-first in the first pass.  Nets that fail -
    because an earlier net consumed the channel they needed - are retried in
    later passes, which is the cheapest useful form of rip-up: the successful
    nets stay put and the failures get another chance in a different order.
    Full rip-up-and-reroute is deliberately not implemented; the report states
    any net that never routes instead of pretending the layout is complete.
    """
    grid = grid or Grid(netlist)
    geometry: dict[str, dict] = {}
    result = RouteResult()

    pending = [n for n in netlist.nets.values() if len(n.pins) > 1 or n.is_port]
    for attempt in range(passes):
        # Port nets go first: their pad end is fixed at the core boundary, so
        # they have the least freedom and suffer most from a congested channel.
        # Remaining nets follow widest-fanout-first, the classical heuristic.
        if attempt == 0:
            ordered = sorted(pending, key=lambda n: (not n.is_port, -len(n.pins), n.name))
        else:
            # Retries keep the same priority order.  Shuffling was tried and
            # made the result worse: a net that succeeds on a retry can push
            # another net out, so a deterministic order at least makes the
            # outcome reproducible.
            ordered = sorted(pending, key=lambda n: (not n.is_port, -len(n.pins), n.name))
        still_failing = []
        for net in ordered:
            # A wider fan on retries was tried and made the result worse:
            # competing retries claim more access points and push each other
            # out.  The fan stays at 2 for every pass.
            if not _route_net(netlist, grid, net, geometry, fan=2):
                still_failing.append(net)
            else:
                net_wires = geometry[net.name]["wires"]
                net_vias = geometry[net.name]["vias"]
                result.routed += 1
                for layer, x0, y0, x1, y1 in net_wires:
                    length = (x1 - x0) if layer == "M1" else (y1 - y0)
                    result.wire_length_um += length
                    result.layer_usage[layer] = result.layer_usage.get(layer, 0.0) + length
                result.vias += len(net_vias)
        pending = still_failing
        if not pending:
            break

    result.failed = [n.name for n in pending]
    return result, geometry
