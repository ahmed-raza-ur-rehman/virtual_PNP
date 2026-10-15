# Verification & validation evidence

**Document:** VP-VER-001 · **Version:** 2.1
Every claim in this file is produced by a command in the repository; nothing is
transcribed by hand.  Re-run `make verify-all` (or `make bootstrap` on a clean
machine first) to regenerate.

---

## 1. Level 1 - unit and property tests (software)

| Command | Evidence | Result |
| --- | --- | --- |
| `make test` | pytest summary | 26 tests, all pass |
| `make lint` | ruff | clean |
| `make cpp-test` | CTest / direct run | optimiser and planner tests pass |
| `make asm-test` | assembled and executed | `hypot(3,4)=5`, `dot=32` |
| `make fw-test` | host-compiled firmware unit tests | pass |

Coverage of the RTL and the placement helpers is intentionally unit-level: the
simulator and the optimisers are tested with known-good versus known-bad
inputs (see `tests/test_asic_flow.py` for the DRC/connectivity cases).

## 2. Level 2 - formal property verification (RTL)

SymbiYosys with the `z3` engine; each task proves its properties *and* proves
that its target states are reachable (covers), so a proof cannot pass
vacuously.

| Task | Properties proved |
| --- | --- |
| `seq_div_props` | `quotient*divisor + remainder == dividend`; `remainder < divisor`; divide-by-zero reported, never silently wrong; `done` only after a run started |
| `watchdog_props` | early kick flagged; late kick trips and latches; a legal kick clears the counter; a fault acknowledgement restarts the window |
| `limit_monitor_props` | trips latch; `motion_inhibit` follows the filtered channels combinationally; a clear is refused while a channel is asserted |
| `quad_decoder_props` | at most ±1 count per clock; no counting while disabled; index captured |

Run: `make formal` → `verification/reports/formal/*.log`, `summary.json`.

## 3. Level 3 - dynamic simulation of the synthesised netlists

`make rtl-sim` runs six testbenches against the **gate netlist** produced by
`yosys synth` + `abc`, using the repository's own simulator
(`tools/rtlsim`), and writes VCD waveforms.

| Testbench | Contract checked |
| --- | --- |
| `crc_vectors` | CCITT check value of `"123456789"` is 0x29B1 |
| `seq_div_random` | quotient/remainder match Python integer division for 40 random operand pairs |
| `watchdog_window` | early/late/punctual kicks and fault latching |
| `quad_decoder_motion` | forward and reverse counting, index capture, freeze when disabled |
| `uart_tx_framing` | start/stop framing and LSB-first payload recovery |
| `spi_packet_link` | a CRC-protected frame is accepted; bad CRC and bad length are rejected and counted |

Report: `verification/reports/sim/summary.json`, waveforms:
`verification/reports/waves/*.vcd`.

## 4. Level 4 - synthesis and area

`make hdl-lint` elaborates every block and runs `check`; `make hdl-synth`
maps each block to a gate netlist and reports cells, flops and an area
estimate.  Block-level figures are in `verification/reports/synth/summary.json`.

## 5. Level 5 - layout and sign-off

`make asic` runs the mini RTL-to-GDSII flow (see `docs/asic_miniflow.md`) and
produces, per design: a GDSII file, a JSON database and a Markdown report
covering placement quality, routing completion, DRC, connectivity and timing.
The report states `INCOMPLETE` with reasons whenever a stage does not close.

## 6. Defects found by this evidence

Verification that finds nothing has usually not verified anything.  Details of
the defects these levels found before any hardware existed:

| # | Component | Defect | Found by |
| --- | --- | --- | --- |
| 1 | `seq_div` | accumulated repeated subtractions instead of restoring division; any dividend ≥ W·divisor saturated | formal P2 |
| 2 | `watchdog_wwdg` | fault acknowledgement did not restart the window, leaving the counter beyond `WIN_HIGH` with the request cleared | formal P3/P4 |
| 3 | `watchdog_wwdg` | trip raised one cycle after the counter passed the window bound | formal P3b |
| 4 | `limit_monitor` | registered inhibit added a clock of latency to the stop path | formal P3 |
| 5 | `packet_if` | the second sync byte was folded into the CRC, so every well-formed frame failed on the host | `spi_packet_link` |
| 6 | `packet_if` | both CRC bytes were fed back into the running CRC before the comparison | `packet_if` vectors |
| 7 | `asic` library | two pins of one cell snapped onto the same column, shorting them in extraction | connectivity check |
| 8 | `asic` placer | unconstrained swaps moved cells out of row packing (25 overlapping pairs) | placement legality check |
| 9 | `asic` DRC | wires drawn a full pitch wide left no spacing between neighbours | DRC |
| 10 | `rtlsim` | constant-1 connections read as zero, so constant-driven flops looked dead | `quad_decoder_motion` |

## 7. Open items (honest status)

| Item | Status | Impact |
| --- | --- | --- |
| Routing completion on the larger blocks | 90-99 % depending on block | unrouted nets are listed per net in the report; the flow does not claim closure |
| Connectivity extraction cleanup | mismatch reported on `crc16_ccitt`, under investigation | DRC is clean and timing closes; extracted connectivity needs a second pass before it can gate a release |
| Clock/reset tree | not implemented | high-fanout nets are the routing bottleneck and the timing numbers are optimistic without a tree |
| `pnp_core` full block through the flow | runs but is dominated by the reset/clock nets | documented, not hidden |
