#!/usr/bin/env python3
"""Functional testbenches executed against the synthesised netlists.

Each testbench drives the *netlist* (not the RTL source) through the pins of
the block and checks an observable contract:

======================  =====================================================
testbench               what it proves
======================  =====================================================
crc_vectors             the CCITT check value of "123456789" and random frames
seq_div_random          quotient/remainder against Python's integer division
watchdog_window         trip windows for early, late and punctual kicks
quad_decoder_motion     direction decode, index capture and filter behaviour
uart_tx_framing         start/stop framing and bit timing of the transmitter
spi_packet_link         a full CRC-protected command frame over SPI
======================  =====================================================

Running ``python -m rtlsim.testbenches --all`` regenerates every result and
optionally dumps VCD waveforms for inspection.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from rtlsim.netlist import load_design
from rtlsim.sim import Simulation
from rtlsim.vcd import VCDWriter

BUILD = ROOT / "synthesis" / "build" / "sim"


@dataclass
class Result:
    name: str
    status: str = "pass"
    checks: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def check(self, condition: bool, description: str) -> None:
        if condition:
            self.checks.append(description)
        else:
            self.failures.append(description)
            self.status = "fail"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "checks": len(self.checks),
            "failures": self.failures,
        }


# --------------------------------------------------------------------------- #
# netlist generation
# --------------------------------------------------------------------------- #
def find_yosys() -> str:
    for cand in (ROOT / "tools" / "bin" / "yosys", ROOT / ".venv" / "bin" / "yowasp-yosys"):
        if cand.exists():
            return str(cand)
    raise SystemExit("yosys not found - run scripts/bootstrap.sh")


def synthesize(top: str, files: list[str], params: dict[str, int] | None = None) -> Path:
    """Synthesise a design for simulation, caching the gate netlist.

    A dedicated cache directory is used so that the simulation netlists (which
    often override parameters to keep the testbench short) never overwrite the
    area/timing netlists produced by ``make hdl-synth``.
    """
    BUILD.mkdir(parents=True, exist_ok=True)
    out = BUILD / f"{top}.json"
    chparams = " ".join(f"-chparam {k} {v}" for k, v in (params or {}).items())
    script = [
        f"read_verilog -sv -I rtl/common {' '.join(files)}",
        f"hierarchy -top {top} {chparams}".strip(),
        f"synth -top {top} -flatten",
        f"write_json {out.relative_to(ROOT)}",
        "stat",
    ]
    subprocess.run(
        [find_yosys(), "-q", "-p", "; ".join(script)], check=True, cwd=ROOT, capture_output=True
    )
    return out


def simulate(
    top: str,
    files: list[str],
    params: dict[str, int] | None = None,
    clock_period: int = 10,
    trace: tuple[str, ...] = (),
    waves_dir: Path | None = None,
) -> tuple[Simulation, VCDWriter | None]:
    netlist = synthesize(top, files, params)
    design = load_design(netlist, top=top)
    writer = None
    if waves_dir is not None and trace:
        writer = VCDWriter(waves_dir / f"{top}.vcd").open()
        for signal in trace:
            writer.add(signal, 1)
    sim = Simulation(design, clock_period=clock_period, vcd=writer, trace_signals=trace)
    return sim, writer


def reset(sim: Simulation, cycles: int = 3) -> None:
    sim.set("rst_n", 0)
    sim.run(cycles)
    sim.set("rst_n", 1)
    sim.clock_edge()


# --------------------------------------------------------------------------- #
# reference models
# --------------------------------------------------------------------------- #
def crc16_ccitt(data: bytes, init: int = 0xFFFF) -> int:
    crc = init
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


# --------------------------------------------------------------------------- #
# testbenches
# --------------------------------------------------------------------------- #
def tb_crc_vectors(waves: Path | None) -> Result:
    res = Result("crc_vectors")
    sim, writer = simulate(
        "crc16_ccitt", ["rtl/comm/crc16_ccitt.sv"], trace=("crc",), waves_dir=waves
    )
    reset(sim)
    payload = b"123456789"
    for byte in payload:
        sim.set("data", byte)
        sim.set("start", 1)
        sim.clock_edge()
        sim.set("start", 0)
        sim.clock_edge()
    got = sim.get("crc")
    expected = crc16_ccitt(payload)
    res.check(got == expected, f'check value of "123456789" 0x{got:04X} == 0x{expected:04X}')
    if writer:
        writer.close()
    return res


def tb_seq_div_random(waves: Path | None) -> Result:
    import random

    res = Result("seq_div_random")
    sim, writer = simulate(
        "seq_div", ["rtl/common/seq_div.sv"], params={"W": 8}, trace=("done",), waves_dir=waves
    )
    reset(sim)

    def divide(a: int, b: int) -> tuple[int, int]:
        sim.set("dividend", a)
        sim.set("divisor", b)
        sim.set("start", 1)
        sim.clock_edge()
        sim.set("start", 0)
        for _ in range(20):
            sim.clock_edge()
            if sim.get("done"):
                break
        return sim.get("quotient"), sim.get("remainder")

    rng = random.Random(20261015)
    ok_q = ok_r = 0
    for _ in range(40):
        a, b = rng.randrange(256), rng.randrange(1, 256)
        q, r = divide(a, b)
        ok_q += q == a // b
        ok_r += r == a % b
    res.check(ok_q == 40, f"quotient matches for {ok_q}/40 random operands")
    res.check(ok_r == 40, f"remainder matches for {ok_r}/40 random operands")

    q, r = divide(0x80, 0)
    res.check(q == 0xFF and r == 0, f"divide-by-zero reports saturation (q=0x{q:02X}, r={r})")
    if writer:
        writer.close()
    return res


def tb_watchdog_window(waves: Path | None) -> Result:
    res = Result("watchdog_window")
    sim, writer = simulate(
        "watchdog_wwdg",
        ["rtl/safety/watchdog_wwdg.sv"],
        params={"WIN_LOW": 4, "WIN_HIGH": 16},
        trace=("reset_req", "early_kick"),
        waves_dir=waves,
    )
    reset(sim)

    sim.set("kick", 1)  # kick immediately: too early
    sim.clock_edge()
    sim.set("kick", 0)
    res.check(sim.get("early_kick") == 1, "kick inside the lower window raises early_kick")

    sim.set("clear_fault", 1)
    sim.clock_edge()
    sim.set("clear_fault", 0)
    sim.clock_edge()

    sim.set("kick", 0)  # then stop kicking entirely
    for _ in range(20):
        sim.clock_edge()
    res.check(sim.get("reset_req") == 1, "a missed kick raises reset_req")

    for _ in range(5):  # the fault must survive a good kick
        sim.set("kick", 1)
        sim.clock_edge()
        sim.set("kick", 0)
    res.check(sim.get("reset_req") == 1, "reset_req is sticky across later kicks")

    sim.set("clear_fault", 1)
    sim.clock_edge()
    sim.set("clear_fault", 0)
    sim.clock_edge()
    res.check(sim.get("reset_req") == 0, "an explicit clear releases reset_req")
    if writer:
        writer.close()
    return res


def tb_quad_decoder_motion(waves: Path | None) -> Result:
    res = Result("quad_decoder_motion")
    sim, writer = simulate(
        "quad_decoder",
        ["rtl/motion/quad_decoder.sv"],
        params={"CNT_W": 16, "FILTER_LEN": 1},
        trace=("moving",),
        waves_dir=waves,
    )
    reset(sim)
    sim.set("count_en", 1)

    # A quadrature cycle is four states; each transition between adjacent
    # states is one count.  The expected count is derived from the stimulus
    # itself so that the testbench documents the encoder arithmetic instead of
    # hard-coding a magic number.
    cycle = [(0, 0), (0, 1), (1, 1), (1, 0)]
    SETTLE = 6  # input synchroniser + glitch filter latency

    def drive(states: list[tuple[int, int]]) -> int:
        """Drive a state sequence, returning the number of transitions."""
        for a, b in states:
            sim.set("a_raw", a)
            sim.set("b_raw", b)
            sim.run(SETTLE)
        return sum(1 for i in range(1, len(states)) if states[i] != states[i - 1])

    forward_states = cycle * 5  # starts and ends at 00
    expected_fwd = drive(forward_states)
    count_after_forward = sim.get("count")
    res.check(
        count_after_forward == expected_fwd,
        f"{expected_fwd} forward quadrature edges counted ({count_after_forward})",
    )
    res.check(sim.get("dir") == 1, "direction reported as increasing")

    reverse_states = list(reversed(cycle)) * 3
    expected_rev = drive(reverse_states)
    count_after_reverse = sim.get("count")
    res.check(
        count_after_reverse == expected_fwd - expected_rev,
        f"reverse counts back down ({count_after_reverse})",
    )
    res.check(sim.get("dir") == 0, "direction reported as decreasing")

    sim.set("idx_raw", 0)
    sim.run(SETTLE)
    sim.set("idx_raw", 1)
    sim.run(SETTLE)
    res.check(sim.get("index_seen") == 1, "index pulse captured")
    res.check(
        sim.get("index_pos") == count_after_reverse, "index position latched at the index edge"
    )

    sim.set("count_en", 0)
    before = sim.get("count")
    for a, b in cycle:
        sim.set("a_raw", a)
        sim.set("b_raw", b)
        sim.run(SETTLE)
    res.check(sim.get("count") == before, "the counter freezes when counting is disabled")
    if writer:
        writer.close()
    return res


def tb_uart_tx_framing(waves: Path | None) -> Result:
    res = Result("uart_tx_framing")
    # CLK_HZ/BAUD chosen so that BAUD_DIV = 8 keeps the trace readable
    sim, writer = simulate(
        "uart_tx",
        ["rtl/comm/uart_tx.sv"],
        params={"CLK_HZ": 80, "BAUD": 10, "BAUD_DIV": 8},
        trace=("tx",),
        waves_dir=waves,
    )
    reset(sim)
    sim.set("data", 0xA5)
    sim.set("valid", 1)
    sim.clock_edge()
    res.check(
        sim.get("ready") == 0, "the transmitter marks itself not ready once a byte is accepted"
    )
    sim.set("valid", 0)

    # The line goes low one clock after the byte is accepted, then each bit is
    # BAUD_DIV cycles wide; sampling at bit centres recovers the frame.
    sim.run(1)
    samples = []
    for _ in range(10):
        samples.append(sim.get("tx") & 1)
        sim.run(8)
    res.check(samples[0] == 0, "start bit is low")
    bits = samples[1:9]
    byte = sum(bit << i for i, bit in enumerate(bits))
    res.check(byte == 0xA5, f"payload recovered LSB first (0x{byte:02X})")
    res.check(samples[9] == 1, "stop bit is high")
    sim.run(8)
    res.check(sim.get("ready") == 1, "the transmitter is ready for the next byte")
    if writer:
        writer.close()
    return res


def tb_spi_packet_link(waves: Path | None) -> Result:
    res = Result("spi_packet_link")
    sim, writer = simulate(
        "spi_packet_harness",
        [
            "rtl/comm/spi_slave.sv",
            "rtl/comm/crc16_ccitt.sv",
            "rtl/comm/packet_if.sv",
            "verification/tb/harness/spi_packet_harness.sv",
        ],
        params={"MAX_PAYLOAD": 8, "LEN_W": 4, "TIMEOUT": 100000},
        trace=("frames_ok", "frames_err"),
        waves_dir=waves,
    )
    reset(sim)
    sim.set("cs_n", 1)
    sim.set("sck", 0)

    trail: list[tuple[int, int, int, int]] = []

    def send(bytes_: list[int]) -> None:
        sim.set("cs_n", 0)
        sim.run(2)
        for byte in bytes_:
            for bit in range(8):
                sim.set("mosi", (byte >> (7 - bit)) & 1)  # SPI is MSB first
                sim.set("sck", 1)
                sim.clock_edge()
                sim.set("sck", 0)
                sim.clock_edge()
        sim.set("cs_n", 1)
        sim.run(10)  # let the framer settle (error counters update late)
        trail.append(
            (
                sim.get("frames_ok"),
                sim.get("frames_err"),
                sim.get("err_bad_crc"),
                sim.get("err_bad_len"),
            )
        )

    payload = bytes([0x11, 0x22, 0x33, 0x44])
    frame = bytes([0xAA, 0x55, 0x01, len(payload)]) + payload
    crc = crc16_ccitt(frame[2:])
    send(list(frame) + [crc >> 8, crc & 0xFF])
    sim.run(2)
    res.check(
        sim.get("frames_ok") == 1,
        f"a valid frame is accepted (frames_ok == {sim.get('frames_ok')})",
    )
    res.check(sim.get("err_bad_crc") == 0, "a valid frame does not raise a CRC error")

    bad = bytes([0xAA, 0x55, 0x02, 4]) + payload + bytes([0x00, 0x00])
    send(list(bad))
    sim.run(2)
    res.check(sim.get("err_bad_crc") == 1, "a corrupted CRC is rejected")
    res.check(sim.get("frames_ok") == 1, "the rejected frame is not counted as good")

    bad_len = bytes([0xAA, 0x55, 0x03, 0x00])
    send(list(bad_len))
    sim.run(4)  # let the parser settle after the final byte
    res.check(sim.get("err_bad_len") == 1, "a zero-length payload is rejected")
    res.check(sim.get("frames_err") >= 2, f"the error counter advances (trail={trail})")
    if writer:
        writer.close()
    return res


TESTBENCHES = {
    "crc_vectors": tb_crc_vectors,
    "seq_div_random": tb_seq_div_random,
    "watchdog_window": tb_watchdog_window,
    "quad_decoder_motion": tb_quad_decoder_motion,
    "uart_tx_framing": tb_uart_tx_framing,
    "spi_packet_link": tb_spi_packet_link,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="run every testbench")
    parser.add_argument("--only", nargs="*", default=None)
    parser.add_argument("--waves", default=None, help="directory for VCD output")
    args = parser.parse_args(argv)

    selected = args.only or list(TESTBENCHES)
    waves = Path(args.waves) if args.waves else None
    if waves:
        (ROOT / waves).mkdir(parents=True, exist_ok=True)

    results = []
    for name in selected:
        if name not in TESTBENCHES:
            print(f"unknown testbench: {name}")
            return 2
        print(f"== {name}")
        try:
            res = TESTBENCHES[name](waves)
        except Exception as exc:  # noqa: BLE001 - reported, not swallowed
            res = Result(name, status="error")
            res.failures.append(f"{type(exc).__name__}: {exc}")
        for line in res.checks:
            print(f"   PASS  {line}")
        for line in res.failures:
            print(f"   FAIL  {line}")
        results.append(res)

    report_dir = ROOT / "verification" / "reports" / "sim"
    report_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "testbenches": [r.to_dict() for r in results],
        "passed": sum(1 for r in results if r.status == "pass"),
        "failed": sum(1 for r in results if r.status != "pass"),
        "checks": sum(len(r.checks) for r in results),
    }
    (report_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(
        f"\n{summary['passed']} passed, {summary['failed']} failed, "
        f"{summary['checks']} assertions checked"
    )
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
