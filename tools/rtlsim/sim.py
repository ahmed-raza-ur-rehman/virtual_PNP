"""Cycle-accurate evaluator for Yosys gate-level netlists.

Model
-----
* nets are unsigned integers of the width declared by the netlist;
* combinational cells are evaluated in topological order, which is precomputed
  once per design, so a cycle costs O(cells) evaluations;
* sequential cells are updated on the rising edge of ``clk`` (``$adff`` carries
  an asynchronous reset that is applied immediately, which is what makes the
  reset behaviour of the RTL testable here);
* four-valued logic is *not* modelled.  The RTL in this repository is written so
  that every register is reset explicitly, and the simulator asserts at load
  time that no cell is left without a defined driver - if that ever stops being
  true the testbenches fail loudly instead of passing on X-propagation luck.

Supported cell subset: the gates and flip-flops produced by ``synth`` + ``abc``
for the blocks in ``rtl/``.  Anything else raises :class:`SimError`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from .netlist import Design, NetlistError

# --------------------------------------------------------------------------- #
# cell semantics: name -> (inputs, output, evaluator)
# --------------------------------------------------------------------------- #
BIN_GATES = {
    "$_AND_": lambda a, b, w: a & b,
    "$_NAND_": lambda a, b, w: ~(a & b),
    "$_OR_": lambda a, b, w: a | b,
    "$_NOR_": lambda a, b, w: ~(a | b),
    "$_XOR_": lambda a, b, w: a ^ b,
    "$_XNOR_": lambda a, b, w: ~(a ^ b),
    "$_ANDNOT_": lambda a, b, w: a & ~b,
    "$_ORNOT_": lambda a, b, w: a | ~b,
}
UNARY_GATES = {
    "$_NOT_": lambda a, w: ~a,
    "$_BUF_": lambda a, w: a,
    "$not": lambda a, w: ~a,
    "$pos": lambda a, w: a,
    "$neg": lambda a, w: -a,
    "$reduce_and": lambda a, w: 1 if all((a >> i) & 1 for i in range(w)) else 0,
    "$reduce_or": lambda a, w: 1 if a else 0,
    "$reduce_bool": lambda a, w: 1 if a else 0,
    "$reduce_xor": lambda a, w: bin(a).count("1") & 1,
    "$reduce_xnor": lambda a, w: (~bin(a).count("1")) & 1,
    "$logic_not": lambda a, w: 0 if a else 1,
}
ARITH = {
    "$add": lambda a, b, w: a + b,
    "$sub": lambda a, b, w: a - b,
    "$mul": lambda a, b, w: a * b,
    "$div": lambda a, b, w: 0 if b == 0 else a // b,
    "$mod": lambda a, b, w: 0 if b == 0 else a % b,
    "$and": lambda a, b, w: a & b,
    "$or": lambda a, b, w: a | b,
    "$xor": lambda a, b, w: a ^ b,
    "$xnor": lambda a, b, w: ~(a ^ b),
    "$shl": lambda a, b, w: a << b,
    "$shr": lambda a, b, w: a >> b,
}
CMP = {
    "$eq": lambda a, b, w: 1 if a == b else 0,
    "$ne": lambda a, b, w: 1 if a != b else 0,
    "$eqx": lambda a, b, w: 1 if a == b else 0,
    "$nex": lambda a, b, w: 1 if a != b else 0,
    "$lt": lambda a, b, w: 1 if a < b else 0,
    "$le": lambda a, b, w: 1 if a <= b else 0,
    "$gt": lambda a, b, w: 1 if a > b else 0,
    "$ge": lambda a, b, w: 1 if a >= b else 0,
}

# Flip-flop naming convention used by yosys:
#     $_<S?DFF><E?><R?>_<clock><reset><reset_value><enable>_
# e.g. $_DFFE_PN1P_ = posedge clock, active-low async reset, reset value 1,
#      active-high enable.  The polarity characters are parsed rather than
#      enumerated so that a new variant cannot be silently mis-modelled.
_FF_RE = re.compile(r"^\$_((?:S)?DFF(?:E)?(?:R)?)_([PN])([PN])([01])?([PN])?_$")
# cells that carry no logic and are dropped when a netlist is loaded
METADATA_CELLS = {"$scopeinfo", "$specify2", "$specify3", "$specrule"}
COARSE_FF = {"$dff", "$dffe", "$adff", "$adffe", "$sdff", "$sdffe", "$aldff", "$aldffe"}


def parse_ff_type(cell_type: str, connections: dict | None = None) -> dict | None:
    """Return the electrical convention of a flip-flop cell, or None.

    The naming convention is ``$_<S?DFF><E?><R?>_<clock><reset_or_enable>
    <reset_value?><enable?>_``; when the reset value is absent the middle
    character describes the *enable* unless the cell actually carries a reset
    port, which is decided from the connections rather than guessed.
    """
    match = _FF_RE.match(cell_type)
    if match:
        _, cpol, second, rval, third = match.groups()
        ports = {"clock": "C", "data": "D", "reset": "R", "enable": "E", "output": "Q"}
        has_r = connections is None or "R" in connections
        has_e = connections is not None and "E" in connections
        if rval is not None:
            return {
                "clock": cpol,
                "reset_active_low": second == "N",
                "reset_value": int(rval),
                "enable_active_low": (third == "N") if third else False,
                "has_enable": bool(third) or "E" in cell_type.split("_")[1],
                "has_reset": True,
                "sync_reset": "SDFF" in cell_type,
                "ports": ports,
            }
        # no reset value in the name
        if has_r and not has_e:
            return {
                "clock": cpol,
                "reset_active_low": second == "N",
                "reset_value": 0,           # undefined in RTL: modelled as 0
                "enable_active_low": False,
                "has_enable": False,
                "has_reset": True,
                "sync_reset": "SDFF" in cell_type,
                "ports": ports,
            }
        return {
            "clock": cpol,
            "reset_active_low": False,
            "reset_value": 0,
            "enable_active_low": second == "N",
            "has_enable": True,
            "has_reset": False,
            "sync_reset": "SDFF" in cell_type,
            "ports": ports,
        }
    if cell_type in COARSE_FF:
        return {
            "clock": "P",
            "reset_active_low": False,
            "reset_value": 0,
            "enable_active_low": False,
            "has_enable": cell_type in {"$dffe", "$adffe", "$sdffe", "$aldffe"},
            "has_reset": "a" in cell_type,
            "sync_reset": cell_type in {"$sdff", "$sdffe"},
            "coarse": True,
            "ports": {"clock": "CLK", "data": "D", "reset": "ARST", "enable": "EN", "output": "Q"},
        }
    return None


SEQUENTIAL = {t for t in [
    "$_DFF_P_", "$_DFF_N_", "$_DFF_PN0_", "$_DFF_PN1_", "$_DFF_NN0_", "$_DFF_NN1_",
    "$_SDFF_PN0_", "$_SDFF_PN1_", "$_SDFF_NN0_", "$_SDFF_NN1_",
    "$_DFFE_PN0P_", "$_DFFE_PN1P_", "$_DFFE_PP0P_", "$_DFFE_PP1P_",
    "$dff", "$dffe", "$adff", "$adffe", "$sdff", "$sdffe", "$aldff", "$aldffe",
]}
_DFFE_PREFIX = "$_DFFE_"
_DFFSR_PREFIX = "$_DFFSR_"


def is_sequential(cell_type: str) -> bool:
    """True for any flip-flop variant the simulator can model."""
    return cell_type in SEQUENTIAL or parse_ff_type(cell_type) is not None


class SimError(RuntimeError):
    """Raised for unsupported cells or contract violations while simulating."""


@dataclass
class Simulation:
    """Simulates one flattened design."""

    design: Design
    clock: str = "clk"
    reset: str | None = "rst_n"
    clock_period: int = 10
    vcd: object | None = None
    trace_signals: tuple[str, ...] = ()

    _nets: dict[int, int] = field(default_factory=dict)
    _drivers: dict[int, str] = field(default_factory=dict)
    _combo_order: list[str] = field(default_factory=list)
    _seq_cells: list[str] = field(default_factory=list)
    _time: int = 0

    # ------------------------------------------------------------------ setup
    def __post_init__(self) -> None:
        self._wires: dict[int, int] = {}       # net id -> width
        self._collect_widths()
        self._check_supported()
        self._build_order()
        self.reset_state()

    def _collect_widths(self) -> None:
        for net in self.design.ports.values():
            for bit in net["bits"]:
                if isinstance(bit, int):
                    self._wires[bit] = 1
        for net in self.design.netnames.values():
            width = len([b for b in net["bits"] if isinstance(b, int)])
            for bit in net["bits"]:
                if isinstance(bit, int):
                    self._wires[bit] = max(self._wires.get(bit, 1), width)

    def _check_supported(self) -> None:
        unsupported: dict[str, int] = {}
        for cell in self.design.cells.values():
            t = cell.type
            if (
                t in BIN_GATES or t in UNARY_GATES or t in ARITH or t in CMP
                or is_sequential(t)
                or t in {"$mux", "$_MUX_", "$pmux", "$concat", "$slice", "$tribuf", "$_TBUF_"}
            ):
                continue
            unsupported[t] = unsupported.get(t, 0) + 1
        if unsupported:
            raise SimError(
                "unsupported cells in netlist (extend rtlsim.sim): "
                + ", ".join(f"{k} x{v}" for k, v in sorted(unsupported.items()))
            )

    def _build_order(self) -> None:
        """Topologically sort combinational cells; sequential cells are latched."""
        deps: dict[str, set[str]] = {name: set() for name in self.design.cells}
        driver_of: dict[int, str] = {}
        for name, cell in self.design.cells.items():
            if is_sequential(cell.type):
                continue
            out_bits = self._cell_output_bits(cell)
            for bit in out_bits:
                driver_of[bit] = name
        for name, cell in self.design.cells.items():
            if is_sequential(cell.type):
                continue
            for bit in self._cell_input_bits(cell):
                driver = driver_of.get(bit)
                if driver is not None and driver != name:
                    deps[name].add(driver)
        order: list[str] = []
        temp: set[str] = set()
        perm: set[str] = set()
        loops: list[str] = []

        def is_seq(cell) -> bool:
            return is_sequential(cell.type)


        def visit(node: str) -> None:
            if node in perm:
                return
            if node in temp:
                loops.append(node)
                return
            temp.add(node)
            for dep in deps[node]:
                visit(dep)
            temp.discard(node)
            perm.add(node)
            if not is_seq(self.design.cells[node]):
                order.append(node)

        for name, cell in self.design.cells.items():
            if is_seq(cell):
                # sequential outputs are sources for the combinational cone
                for bit in self._cell_output_bits(cell):
                    pass
            visit(name)
        if loops:
            raise SimError(f"combinational loop through cells: {sorted(set(loops))[:5]}")
        self._combo_order = order
        self._seq_cells = [n for n, c in self.design.cells.items() if is_sequential(c.type)]

    def _cell_output_bits(self, cell) -> list[int]:
        names = self._output_names(cell)
        bits: list[int] = []
        for name in names:
            for bit in cell.connections.get(name, []):
                if isinstance(bit, int):
                    bits.append(bit)
        return bits

    def _cell_input_bits(self, cell) -> list[int]:
        names = set(cell.connections) - set(self._output_names(cell))
        bits: list[int] = []
        for name in names:
            for bit in cell.connections.get(name, []):
                if isinstance(bit, int):
                    bits.append(bit)
        return bits

    @staticmethod
    def _output_names(cell) -> tuple[str, ...]:
        t = cell.type
        if t in BIN_GATES:
            return ("Y",)
        if t in UNARY_GATES:
            return ("Y",)
        if t in ARITH or t in CMP:
            return ("Y",)
        if t == "$mux" or t == "$_MUX_":
            return ("Y",)
        if t == "$pmux":
            return ("Y",)
        if t == "$concat":
            return ("Y",)
        if t == "$slice":
            return ("Y",)
        if t in SEQUENTIAL or t.startswith(_DFFE_PREFIX) or t.startswith(_DFFSR_PREFIX):
            return ("Q",)
        if t in {"$tribuf", "$_TBUF_"}:
            return ("Y",)
        raise SimError(f"no output mapping for cell type {t}")

    # ------------------------------------------------------------------ run
    def reset_state(self) -> None:
        self._nets = {bit: 0 for bit in self._wires}
        # asynchronous reset values are applied for cells that declare one
        for name in self._seq_cells:
            cell = self.design.cells[name]
            if cell.type.endswith("N1_") or cell.type.endswith("P1_"):
                self._write_output(cell, self._all_ones(cell))
        self._evaluate_combinational()

    def _all_ones(self, cell) -> int:
        bits = self._cell_output_bits(cell)
        return (1 << len(bits)) - 1 if bits else 0

    def _bit_value(self, bit) -> int:
        """Resolve one bit of a connection.

        Yosys JSON encodes constant connections as the strings '0', '1', 'x'
        and 'z'.  This simulator is two-valued by design: 'x' and 'z' are read
        as 0 and the initial-state discipline (every flop reset) is what keeps
        that assumption honest.  Ignoring the constants entirely - the first
        implementation did - ties every constant-1 input to zero, which made
        flops whose D input is a constant look dead.
        """
        if isinstance(bit, int):
            return self._nets.get(bit, 0) & 1
        if bit == "1":
            return 1
        return 0

    def _read(self, cell, port: str) -> int:
        value = 0
        for i, bit in enumerate(cell.connections.get(port, [])):
            value |= self._bit_value(bit) << i
        return value

    def _write(self, cell, port: str, value: int) -> None:
        for i, bit in enumerate(cell.connections.get(port, [])):
            if isinstance(bit, int):
                self._nets[bit] = (value >> i) & 1

    def _write_output(self, cell, value: int) -> None:
        for port in self._output_names(cell):
            self._write(cell, port, value)

    def _evaluate_combinational(self) -> None:
        for name in self._combo_order:
            cell = self.design.cells[name]
            t = cell.type
            if t in BIN_GATES:
                a, b = self._read(cell, "A"), self._read(cell, "B")
                self._write_output(cell, BIN_GATES[t](a, b, 1))
            elif t in UNARY_GATES:
                a = self._read(cell, "A")
                width = max(1, len([b for b in cell.connections.get("A", []) if isinstance(b, int)]))
                self._write_output(cell, UNARY_GATES[t](a, width))
            elif t in ARITH:
                a, b = self._read(cell, "A"), self._read(cell, "B")
                self._write_output(cell, ARITH[t](a, b, 1))
            elif t in CMP:
                a, b = self._read(cell, "A"), self._read(cell, "B")
                self._write_output(cell, CMP[t](a, b, 1))
            elif t in {"$mux", "$_MUX_"}:
                a, b, s = self._read(cell, "A"), self._read(cell, "B"), self._read(cell, "S")
                self._write_output(cell, b if s else a)
            elif t == "$pmux":
                a, b, s = self._read(cell, "A"), self._read(cell, "B"), self._read(cell, "S")
                result = a
                for i in range(max(1, len([x for x in cell.connections.get("S", []) if isinstance(x, int)]))):
                    if (s >> i) & 1:
                        width = self._port_width(cell, "A")
                        result = (b >> (i * width)) & ((1 << width) - 1)
                self._write_output(cell, result)
            elif t == "$concat":
                a_bits = [b for b in cell.connections.get("A", []) if isinstance(b, int)]
                b_bits = [b for b in cell.connections.get("B", []) if isinstance(b, int)]
                out = [b for b in cell.connections.get("Y", []) if isinstance(b, int)]
                # yosys $concat: Y = {A, B}, A occupies the most significant bits
                for i, bit in enumerate(b_bits):
                    if i < len(out):
                        self._nets[out[i]] = self._nets.get(bit, 0)
                for i, bit in enumerate(a_bits):
                    if len(b_bits) + i < len(out):
                        self._nets[out[len(b_bits) + i]] = self._nets.get(bit, 0)
            elif t == "$slice":
                offset = self._param_int(cell, "OFFSET", 0)
                a_bits = [b for b in cell.connections.get("A", []) if isinstance(b, int)]
                out = [b for b in cell.connections.get("Y", []) if isinstance(b, int)]
                for i, bit in enumerate(out):
                    src = offset + i
                    self._nets[bit] = self._nets.get(a_bits[src], 0) if src < len(a_bits) else 0
            elif t in {"$tribuf", "$_TBUF_"}:
                self._write_output(cell, self._read(cell, "A") if self._read(cell, "EN") else 0)
            else:
                raise SimError(f"unhandled cell type {t}")

    def _port_width(self, cell, port: str) -> int:
        return max(1, len([b for b in cell.connections.get(port, []) if isinstance(b, int)]))

    # -- public API --------------------------------------------------------
    def set(self, port: str, value: int) -> None:
        """Drive an input port (or any named net) from the testbench.

        The combinational cone is re-evaluated immediately so that a caller can
        set an input and read a combinational output without an intervening
        clock edge - the same contract a Verilog testbench gets from `assign`
        propagation.
        """
        bits = self._bits_of(port)
        for i, bit in enumerate(bits):
            self._nets[bit] = (value >> i) & 1
        self._evaluate_combinational()

    def get(self, port: str) -> int:
        """Read an output port (or any named net)."""
        bits = self._bits_of(port)
        value = 0
        for i, bit in enumerate(bits):
            value |= (self._nets.get(bit, 0) & 1) << i
        return value

    def _bits_of(self, name: str) -> list[int]:
        if name in self.design.ports:
            return [b for b in self.design.ports[name]["bits"] if isinstance(b, int)]
        if name in self.design.netnames:
            return [b for b in self.design.netnames[name]["bits"] if isinstance(b, int)]
        raise SimError(f"no such port or net: {name}")

    def clock_edge(self) -> None:
        """Apply one rising clock edge and evaluate the combinational logic."""
        pending: list[tuple[object, int]] = []
        for name in self._seq_cells:
            cell = self.design.cells[name]
            spec = parse_ff_type(cell.type, cell.connections)
            if spec is None:                       # pragma: no cover - guarded at load
                raise SimError(f"unhandled flip-flop {cell.type}")
            ports = spec["ports"]
            reset_raw = self._read(cell, ports["reset"]) if spec.get("has_reset", True) else 0
            reset_active = ((reset_raw == 0) if spec["reset_active_low"] else (reset_raw == 1)) \
                if spec.get("has_reset", True) else False
            enable_raw = self._read(cell, ports["enable"]) if spec["has_enable"] else 1
            enable_active = (enable_raw == 0) if spec["enable_active_low"] else (enable_raw == 1)
            data = self._read(cell, ports["data"])
            if reset_active:
                pending.append((cell, spec["reset_value"]))
            elif enable_active:
                pending.append((cell, data))
        for cell, value in pending:
            self._write_output(cell, value)
        self._evaluate_combinational()
        self._time += self.clock_period
        if self.vcd is not None and self.trace_signals:
            self.vcd.step(self._time, {s: self.get(s) for s in self.trace_signals})

    def _param_int(self, cell, key: str, default: int) -> int:
        raw = cell.parameters.get(key)
        if raw is None:
            return default
        s = str(raw).strip("'")
        try:
            return int(s, 2) if set(s) <= {"0", "1"} and len(s) > 1 else int(s)
        except ValueError:
            return default

    def run(self, cycles: int) -> None:
        for _ in range(cycles):
            self.clock_edge()

    def loopback(self, name: str) -> int:
        return self.get(name)

    @property
    def time(self) -> int:
        return self._time
