"""Minimal Value Change Dump writer.

Waveforms are the artefact a hardware engineer actually looks at, so the
simulator writes standard VCD that opens in GTKWave/Surfer without conversion.
Only the subset needed for scalar and vector nets is emitted.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


class VCDWriter:
    def __init__(self, path: str | Path, timescale: str = "1ns") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.timescale = timescale
        self._handles: dict[str, str] = {}
        self._widths: dict[str, int] = {}
        self._fh = None
        self._time = 0
        self._written_header = False

    # -- setup -------------------------------------------------------------
    def add(self, name: str, width: int) -> None:
        if name in self._handles:
            return
        idx = len(self._handles)
        ident = "".join(chr(33 + (idx // 94) % 94) + chr(33 + idx % 94)) if idx else "!"
        self._handles[name] = ident if ident not in self._handles.values() else f"~{idx}"
        self._widths[name] = width

    def _header(self) -> None:
        scope = self.path.stem
        self._fh.write(f"$date\n  {self._now_string()}\n$end\n")
        self._fh.write("$version\n  virtual-pnp rtlsim\n$end\n")
        self._fh.write(f"$timescale {self.timescale} $end\n")
        self._fh.write(f"$scope module {scope} $end\n")
        for name, ident in self._handles.items():
            self._fh.write(f"$var wire {self._widths[name]} {ident} {name} $end\n")
        self._fh.write("$upscope $end\n$enddefinitions $end\n")
        self._written_header = True

    @staticmethod
    def _now_string() -> str:
        import datetime as _dt

        return _dt.datetime.now().strftime("%a %b %d %H:%M:%S %Y")

    # -- recording ---------------------------------------------------------
    def open(self) -> "VCDWriter":
        self._fh = self.path.open("w", encoding="utf-8")
        self._time = 0
        self._header()
        return self

    def step(self, t: int, values: dict[str, int]) -> None:
        if self._fh is None or not self._written_header:
            return
        changed: list[tuple[str, str, int]] = []
        for name, value in values.items():
            if name not in self._handles:
                continue
            width = self._widths[name]
            value &= (1 << width) - 1
            if getattr(self, "_last", {}).get(name) == value:
                continue
            changed.append((self._handles[name], name, value))
        if not changed:
            return
        if not hasattr(self, "_last"):
            self._last = {}
        self._last.update({n: v for _, n, v in changed})
        if t != self._time:
            self._fh.write(f"#{t}\n")
            self._time = t
        for ident, name, value in changed:
            if self._widths[name] == 1:
                self._fh.write(f"{value & 1}{ident}\n")
            else:
                self._fh.write(f"b{value:0{self._widths[name]}b} {ident}\n")

    def close(self) -> None:
        if self._fh is not None:
            self._fh.write(f"#{self._time + 1}\n")
            self._fh.close()
            self._fh = None

    def __enter__(self) -> "VCDWriter":
        return self.open()

    def __exit__(self, *exc: object) -> None:
        self.close()

    def names(self) -> Iterable[str]:
        return self._handles
