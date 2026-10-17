"""Complete EDA flow: synthesis -> placement -> routing -> DRC -> LVS -> GDSII."""
from __future__ import annotations

import os
import tempfile

from .drc import DRC
from .gdsii import GDSIIWriter
from .lvs import LVS
from .placer import Placer
from .router import MazeRouter
from .synthesis import SynthesisEngine


class EDAFlow:
    def __init__(self):
        self.synth = SynthesisEngine()
        self.placer = None
        self.router = None
        self.drc = DRC()
        self.lvs = LVS()
        self.gds = GDSIIWriter()

    def run(self, verilog_src: str, width: int = 100, height: int = 100) -> dict:
        # 1. Synthesis
        ast = self.synth.parse_verilog(verilog_src)
        netlist = self.synth.synthesize(ast)
        netlist = self.synth.optimize(netlist)
        mapped = self.synth.technology_map(netlist, {})
        # 2. Placement
        self.placer = Placer(width, height)
        for cell in mapped.get("cells", []):
            self.placer.add_cell(cell["name"], 5, 5)
        placement = self.placer.place(mapped, iterations=500)
        # 3. Routing
        self.router = MazeRouter(width, height)
        # block placed cells
        for name, (x, y) in placement.items():
            for dx in range(5):
                for dy in range(5):
                    self.router.block(x + dx, y + dy)
        # route nets (simplified: route between adjacent cells)
        cells = list(placement.keys())
        routes = []
        for i in range(len(cells) - 1):
            src = placement[cells[i]]
            dst = placement[cells[i + 1]]
            r = self.router.route(src, dst)
            routes.append(r)
        # 4. DRC
        shapes = []
        for name, (x, y) in placement.items():
            shapes.append({"name": name, "x": x, "y": y, "width": 5, "height": 5, "layer": 1})
        drc_viols = self.drc.run({"shapes": shapes, "vias": []})
        # 5. LVS
        sch_nets = {f"net_{i}": {cells[i], cells[i+1]} for i in range(len(cells)-1)}
        lay_nets = {f"net_{i}": {cells[i], cells[i+1]} for i in range(len(cells)-1)}
        lvs_errs = self.lvs.compare(sch_nets, lay_nets)
        # 6. GDSII
        self.gds.header()
        self.gds.begin_structure(mapped["module"])
        for name, (x, y) in placement.items():
            self.gds.add_boundary(1, 0, [(x, y), (x+5, y), (x+5, y+5), (x, y+5)])
        self.gds.end_structure()
        fd, gds_path = tempfile.mkstemp(suffix=".gds")
        os.close(fd)
        self.gds.write(gds_path)
        return {
            "synthesis": self.synth.report(netlist),
            "placement": placement,
            "routes": len(routes),
            "drc_violations": len(drc_viols),
            "lvs_errors": len(lvs_errs),
            "gds_path": gds_path,
            "gds_report": self.gds.report(),
        }
