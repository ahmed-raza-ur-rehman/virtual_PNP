import os
import tempfile

from pnp.eda.drc import DRC
from pnp.eda.gdsii import GDSIIWriter
from pnp.eda.lvs import LVS
from pnp.eda.placer import Placer
from pnp.eda.router import MazeRouter
from pnp.eda.synthesis import SynthesisEngine


def test_synthesis():
    src = "module foo (a, b); input a; output b; assign b = a; endmodule"
    eng = SynthesisEngine()
    ast = eng.parse_verilog(src)
    assert ast["name"] == "foo"
    nl = eng.synthesize(ast)
    assert len(nl["gates"]) >= 1
    opt = eng.optimize(nl)
    assert "gates" in opt


def test_placer():
    p = Placer(50, 50)
    p.add_cell("c1", 5, 5)
    p.add_cell("c2", 5, 5)
    nl = {"cells": [{"name": "c1"}, {"name": "c2"}]}
    pos = p.place(nl, iterations=100)
    assert "c1" in pos and "c2" in pos


def test_router():
    r = MazeRouter(10, 10)
    path = r.route((0, 0), (9, 9))
    assert len(path) > 0
    assert path[0] == (0, 0) and path[-1] == (9, 9)


def test_drc():
    drc = DRC(min_width=1.0, min_spacing=1.0)
    shapes = [{"width": 0.5, "x": 0, "y": 0, "layer": 1}]
    viols = drc.check_width(shapes)
    assert len(viols) == 1
    report = drc.report()
    assert "violations" in report


def test_lvs():
    lvs = LVS()
    sch = {"net1": {"a", "b"}, "net2": {"c"}}
    lay = {"net1": {"a", "b"}, "net2": {"c"}}
    errs = lvs.compare(sch, lay)
    assert len(errs) == 0


def test_gdsii():
    w = GDSIIWriter()
    w.header()
    w.begin_structure("top")
    w.add_boundary(1, 0, [(0, 0), (10, 0), (10, 10), (0, 10)])
    w.end_structure()
    fd, path = tempfile.mkstemp(suffix=".gds")
    os.close(fd)
    w.write(path)
    assert os.path.exists(path)
    os.remove(path)
