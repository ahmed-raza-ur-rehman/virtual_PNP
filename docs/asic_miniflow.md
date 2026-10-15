# RTL-to-GDSII mini-flow

**Package:** `asic/miniflow` · **Entry point:** `python -m asic.miniflow.flow`
**Make target:** `make asic`

The production path for a large SoC is an open-source *or* commercial RTL-to-GDS
tool chain (the OpenLane configuration in `synthesis/openlane` belongs to that
path).  This package is the other half of the story: a small, fully auditable
flow that goes all the way from a synthesised netlist to a GDSII file and then
*checks its own output*.  It exists so that the platform can demonstrate the
whole chain - synthesis, placement, routing, layout, sign-off - end to end, on
a design small enough that a reviewer can verify every step by hand, with no
licence server and no multi-gigabyte PDK.

## 1. Stages

```
rtl/*.sv ──yosys──> gate netlist (JSON) ──map──> standard-cell netlist
        ──place──> rows + HPWL-improved positions
        ──route──> M1..M5 tracks, vias          ──emit──> GDSII
        ──signoff──> DRC, connectivity, timing  ──report──> Markdown + JSON
```

| Module | Responsibility |
| --- | --- |
| `tech.py` | technology rules, standard-cell library with layouts and pins, yosys-cell → library-cell mapping |
| `netlist_map.py` | reads the yosys JSON netlist, resolves bits to nets, maps gates; refuses unknown gates |
| `placer.py` | connectivity-driven row packing, legality check, annealing over legal row rotations |
| `router.py` | preferred-direction maze router over M1 (channels) … M5, via cost model, retry passes |
| `gdsii.py` | GDSII writer *and* reader (boundary, path, SREF, text, units) |
| `signoff.py` | DRC (width/spacing/enclosure), connectivity extraction, RC-based timing |
| `flow.py` | orchestration, per-stage reporting, JSON + Markdown output |

## 2. Design decisions that matter

**Metal stack with alternating directions.** M1 is confined to the routing
channels above the cells, M2 runs vertically, M3 horizontally and so on.  A
horizontal and a vertical wire can therefore cross without a short, which is
the property that makes maze routing legal on a two-direction stack.

**Uniform minimum-pitch rules.** Every metal shares the same width and spacing
rules, so `pitch >= width + space` holds by construction for every layer.  Real
processes widen upper metals and route them on a coarser pitch; that refinement
is stated as out of scope rather than half-implemented.

**Pin escape geometry.** A cell pin is inside the cell, a track is in the
channel, so the layout contains the stub and the via that join them.  The
router records which access node each pin actually used, and the layout builder
draws the escape to exactly that node - which is what makes the extracted
connectivity match the netlist.

**Same-net shapes are not checked against each other.** Two rectangles of one
net are one conductor; a checker that reports a spacing violation between them
reports a violation no process could avoid.

**Legal moves only.** The placer's annealer rotates a contiguous run inside a
row.  The rotation preserves the run's total width, so every intermediate
placement is legal; the alternative (swap any two cells, then repair) needs a
legaliser, and without one it produced overlapping cells that the legality
check rejected.

## 3. Sign-off scope - what is *not* claimed

| Check | Implemented | Not implemented |
| --- | --- | --- |
| DRC | width, spacing, via enclosure on M1…M5, poly | antenna, density, latch-up, ESD |
| Connectivity | layout-extracted net-by-net comparison with the netlist | transistor-level (device) extraction |
| Timing | library intrinsic delays + Elmore RC on routed wires, setup check at DFFs | clock tree, crosstalk, derating, hold |
| Power | not implemented | - |
| IR drop | not implemented | - |

A run whose routing, DRC, connectivity or timing does not close is reported as
`INCOMPLETE` with the failing items enumerated.  That is deliberate: a flow
that prints "PASS" because it could not see the problem is worse than no flow.

## 4. Results on `crc16_ccitt` (59 library cells)

| Metric | Value |
| --- | --- |
| cells / nets | 59 / 71 |
| cell area | 479 µm² |
| core | ≈ 30 x 36 µm, 7 rows |
| placement | HPWL 288 → 171 µm (−41 %) |
| DRC | 0 violations (≈ 190 000 checks) |
| timing | critical path ≈ 0.26 ns, +9.6 ns slack at 10 ns |
| GDS | `asic/build/crc16_ccitt.gds` |

Routing completion and connectivity extraction for this block are reported in
`asic/build/crc16_ccitt_report.md`; both were still incomplete at the last run
and are tracked as open items rather than hidden.

## 5. Reproducing

```bash
make bootstrap          # pip-installable EDA backend (WASM yosys), no OS packages
make asic               # full flow on the default design
make asic DESIGN=pnp_core   # a multi-block design
cat asic/build/crc16_ccitt_report.md
```

The flow is deterministic: same netlist, same seed, same GDS.
