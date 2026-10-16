#!/usr/bin/env python3
"""HDL flow driver: lint, synthesis and formal verification for the PnP RTL.

The driver is deliberately thin: every step shells out to the open-source
Yosys/SymbiYosys toolchain (native or the `yowasp` WASM build) and writes a
machine-readable report under ``verification/reports/``.  Keeping the flow in
one place means CI, the Makefile and a developer's laptop all execute exactly
the same commands.

Blocks are declared in :data:`BLOCKS`; adding a module to the design means
adding one entry, which is also what the traceability matrix reads.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RTL = ROOT / "rtl"
REPORTS = ROOT / "verification" / "reports"

INCLUDE_DIRS = [RTL / "common"]


@dataclass
class Block:
    """One synthesizable block plus the evidence the flow must produce."""

    name: str
    top: str
    files: list[str]
    clock: str = "clk"
    period_ns: float = 10.0
    formal: list[str] = field(default_factory=list)
    note: str = ""


BLOCKS: dict[str, Block] = {
    "seq_div": Block(
        "seq_div",
        "seq_div",
        ["rtl/common/seq_div.sv"],
        formal=["seq_div_props"],
        note="restoring divider used by the profile planner",
    ),
    "quad_decoder": Block(
        "quad_decoder",
        "quad_decoder",
        ["rtl/motion/quad_decoder.sv"],
        formal=["quad_decoder_props"],
        note="quadrature front end with glitch filter and index capture",
    ),
    "stepgen": Block(
        "stepgen",
        "stepgen",
        ["rtl/motion/stepgen.sv"],
        note="velocity to step DDA converter",
    ),
    "pid_axis": Block(
        "pid_axis",
        "pid_axis",
        ["rtl/motion/pid_axis.sv"],
        note="fixed-point PID with anti-windup",
    ),
    "profile_gen": Block(
        "profile_gen",
        "profile_gen",
        ["rtl/common/seq_div.sv", "rtl/motion/profile_gen.sv"],
        formal=["profile_gen_props"],
        note="jerk-limited setpoint generator",
    ),
    "crc16_ccitt": Block(
        "crc16_ccitt",
        "crc16_ccitt",
        ["rtl/comm/crc16_ccitt.sv"],
        note="CCITT framing CRC",
    ),
    "uart_tx": Block(
        "uart_tx",
        "uart_tx",
        ["rtl/comm/uart_tx.sv"],
        note="8N1 transmitter",
    ),
    "uart_rx": Block(
        "uart_rx",
        "uart_rx",
        ["rtl/comm/uart_rx.sv"],
        note="8N1 receiver with mid-bit sampling",
    ),
    "spi_slave": Block(
        "spi_slave",
        "spi_slave",
        ["rtl/comm/spi_slave.sv"],
        note="mode 0/3 SPI slave with byte strobe",
    ),
    "packet_if": Block(
        "packet_if",
        "packet_if",
        ["rtl/comm/crc16_ccitt.sv", "rtl/comm/packet_if.sv"],
        formal=["packet_if_props"],
        note="length + CRC framed command parser",
    ),
    "csr_bank": Block(
        "csr_bank",
        "csr_bank",
        ["rtl/periph/csr_bank.sv"],
        note="control/status register bank with byte enables",
    ),
    "watchdog_wwdg": Block(
        "watchdog_wwdg",
        "watchdog_wwdg",
        ["rtl/safety/watchdog_wwdg.sv"],
        formal=["watchdog_props"],
        note="window watchdog: kick too early or too late trips",
    ),
    "limit_monitor": Block(
        "limit_monitor",
        "limit_monitor",
        ["rtl/safety/limit_monitor.sv"],
        formal=["limit_monitor_props"],
        note="latching limit/e-stop supervisor",
    ),
    "centroid_accel": Block(
        "centroid_accel",
        "centroid_accel",
        ["rtl/vision/centroid_accel.sv"],
        note="streaming centroid + second-moment orientation accumulator",
    ),
    "pnp_core": Block(
        "pnp_core",
        "pnp_core",
        [
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
        note="full control core: 3 axes, packet interface, safety, vision port",
    ),
}


# --------------------------------------------------------------------------- #
# tool discovery
# --------------------------------------------------------------------------- #
def find_tool(name: str, override: str | None = None) -> str:
    """Locate a tool, preferring the explicit override, then PATH, then .venv."""
    if override:
        return override
    found = shutil.which(name)
    if found:
        return found
    venv = ROOT / ".venv" / "bin" / f"yowasp-{name}"
    if venv.exists():
        return str(venv)
    raise FileNotFoundError(
        f"{name} not found. Install it with `pip install yowasp-yosys yowasp-sby` "
        "or run scripts/bootstrap.sh"
    )


def tool_env() -> dict[str, str]:
    """Environment with the repository tool shims on PATH.

    SymbiYosys shells out to `yosys` and `yosys-smtbmc`; the shims in
    tools/bin map those names onto the WASM builds so the flow runs on a bare
    machine with nothing but pip.
    """
    import os

    env = dict(os.environ)
    extra = f"{ROOT / 'tools' / 'bin'}{os.pathsep}{ROOT / '.venv' / 'bin'}"
    env["PATH"] = f"{extra}{os.pathsep}{env.get('PATH', '')}"
    return env


def run(cmd: list[str], log: Path | None = None, check: bool = True) -> str:
    """Run a command, echo it, optionally tee to a log file."""
    printable = " ".join(cmd)
    print(f"  $ {printable}")
    proc = subprocess.run(
        cmd, capture_output=True, text=True, cwd=ROOT, env=tool_env(), check=False
    )
    out = proc.stdout + proc.stderr
    if log is not None:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(f"$ {printable}\n\n{out}", encoding="utf-8")
    if check and proc.returncode != 0:
        print(out)
        raise SystemExit(f"command failed ({proc.returncode}): {printable}")
    return out


def yosys_script(script: str, yosys: str, log: Path | None = None) -> str:
    return run([yosys, "-q" if False else "-p", script], log=log)


# --------------------------------------------------------------------------- #
# steps
# --------------------------------------------------------------------------- #
STAT_RE = re.compile(r"^\s+(\d+)\s+(\S+)$", re.MULTILINE)


def parse_stat(text: str) -> dict[str, int]:
    """Extract the cell histogram from a Yosys ``stat`` block."""
    if "Printing statistics" not in text:
        return {}
    tail = text.split("Printing statistics")[-1]
    cells: dict[str, int] = {}
    for count, kind in STAT_RE.findall(tail):
        if kind.startswith("$") or kind.isidentifier():
            cells[kind] = int(count)
    return cells


def lint(yosys: str, only: list[str] | None = None) -> dict:
    print("== HDL lint (elaborate + check)")
    summary = {}
    for name, blk in BLOCKS.items():
        if only and name not in only:
            continue
        files = " ".join(blk.files)
        script = (
            f"read_verilog -sv -I {INCLUDE_DIRS[0].relative_to(ROOT)} {files}\n"
            f"hierarchy -top {blk.top}\n"
            f"proc\nopt\ncheck\nstat"
        )
        log = REPORTS / "lint" / f"{name}.log"
        out = yosys_script(script, yosys, log=log)
        cells = parse_stat(out)
        errors = [ln for ln in out.splitlines() if "ERROR" in ln]
        summary[name] = {
            "cells": cells,
            "total_cells": sum(v for k, v in cells.items() if k.startswith("$")),
            "errors": errors,
            "status": "fail" if errors else "pass",
        }
        mark = "FAIL" if errors else "pass"
        print(f"  {name:16s} {mark}  ({summary[name]['total_cells']} cells)")
    (REPORTS / "lint").mkdir(parents=True, exist_ok=True)
    (REPORTS / "lint" / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def synth(yosys: str, only: list[str] | None = None) -> dict:
    """Synthesise to a gate netlist and an area estimate."""
    print("== HDL synthesis (generic + gate level)")
    build = ROOT / "synthesis" / "build"
    build.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, blk in BLOCKS.items():
        if only and name not in only:
            continue
        files = " ".join(blk.files)
        json_out = build / f"{name}.json"
        netlist = build / f"{name}_netlist.sv"
        script = (
            f"read_verilog -sv -I {INCLUDE_DIRS[0].relative_to(ROOT)} {files}\n"
            f"hierarchy -top {blk.top}\n"
            f"synth -top {blk.top} -flatten\n"
            f"opt -fast\n"
            f"write_verilog -noattr {netlist.relative_to(ROOT)}\n"
            f"write_json {json_out.relative_to(ROOT)}\n"
            f"stat"
        )
        log = REPORTS / "synth" / f"{name}.log"
        yosys_script(script, yosys, log=log)
        # The WASM build truncates the console log when ABC maps the design;
        # the JSON netlist is the authoritative artefact, so the histogram is
        # taken from there rather than scraped from stdout.
        data = json.loads(json_out.read_text())
        top_module = data["modules"][blk.top]
        cells: dict[str, int] = {}
        for cell in top_module["cells"].values():
            cells[cell["type"]] = cells.get(cell["type"], 0) + 1
        n_cells = sum(cells.values())
        # crude but useful early estimate: 5 GE per 1-bit register, 4 GE per
        # combinational cell, ~1500 um^2 per GE for a 130 nm low-power library.
        dffs = sum(v for k, v in cells.items() if "dff" in k.lower())
        comb = n_cells - dffs
        gates = 6 * dffs + 4 * comb
        summary[name] = {
            "cells": cells,
            "yosys_cells": n_cells,
            "flops": dffs,
            "combinational": comb,
            "gate_equivalent_estimate": gates,
            "area_um2_estimate_130nm": round(gates * 1.5, 1),
            "clock_period_ns": blk.period_ns,
            "netlist": str(netlist.relative_to(ROOT)),
            "json": str(json_out.relative_to(ROOT)),
        }
        print(
            f"  {name:16s} {n_cells:5d} cells  ~{gates:6d} GE  "
            f"~{summary[name]['area_um2_estimate_130nm']:8.0f} um^2"
        )
    (REPORTS / "synth").mkdir(parents=True, exist_ok=True)
    (REPORTS / "synth" / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def formal(sby: str, yosys: str, only: list[str] | None = None) -> dict:
    print("== formal verification (SymbiYosys)")
    formal_dir = ROOT / "verification" / "formal"
    out_dir = REPORTS / "formal"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    tasks = sorted(formal_dir.glob("*.sby"))
    if not tasks:
        print("  no .sby tasks found")
        return summary
    for task in tasks:
        name = task.stem
        if only and name not in only:
            continue
        log = out_dir / f"{name}.log"
        proc = subprocess.run(
            [sby, "-f", "-d", str(out_dir / name), str(task.relative_to(ROOT))],
            capture_output=True,
            text=True,
            cwd=ROOT,
            env=tool_env(),
            check=False,
        )
        out = proc.stdout + proc.stderr
        log.write_text(f"$ {sby} {task.name}\n\n{out}", encoding="utf-8")
        status = "pass" if proc.returncode == 0 else "fail"
        # SymbiYosys prints one line per engine result; the summary lines are
        # the audit trail attached to the release, so they are captured
        # verbatim rather than summarised.
        result_lines = [ln.strip() for ln in out.splitlines() if re.search(r"\b(PASS|FAIL)\b", ln)]
        cover_lines = [ln.strip() for ln in out.splitlines() if "cover" in ln.lower()]
        summary[name] = {
            "status": status,
            "results": result_lines[-6:],
            "covers": cover_lines[:6],
        }
        print(f"  {name:24s} {status.upper()}")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=["lint", "synth", "formal", "all"])
    parser.add_argument("--yosys", default=None)
    parser.add_argument("--sby", default=None)
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args(argv)

    if args.step in ("lint", "synth", "all"):
        lint(find_tool("yosys", args.yosys), args.only)
    if args.step in ("synth", "all"):
        synth(find_tool("yosys", args.yosys), args.only)
    if args.step in ("formal", "all"):
        formal(find_tool("sby", args.sby), find_tool("yosys", args.yosys), args.only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
