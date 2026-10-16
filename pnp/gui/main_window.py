"""PyQt5 desktop application for the virtual SMD pick & place machine."""

import sys

import numpy as np

try:
    from PyQt5.QtCore import QTimer
    from PyQt5.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QPushButton,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    _QT = True
except ImportError:
    _QT = False

from pnp.algorithms.path_planning import plan_path
from pnp.algorithms.placement_optimizer import optimize_feeders, optimize_placement
from pnp.sim.machine_sim import MachineSim

if not _QT:

    class MainWindow:
        def __init__(self, *a, **k):
            raise RuntimeError("PyQt5/libGL not available in this environment")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Virtual SMD Pick & Place - Professional")
        self.resize(1100, 700)
        self.sim = MachineSim()
        self.targets = self._demo_targets()
        self._build_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)

    def _demo_targets(self):
        types = ["0402", "0603", "0805", "SOIC8", "TQFP32", "LED0603"]
        ts = []
        rng = np.random.default_rng(1)
        for i in range(30):
            ts.append(
                {
                    "id": i,
                    "type": types[i % len(types)],
                    "x": float(rng.uniform(-60, 60)),
                    "z": float(rng.uniform(-40, 40)),
                    "rotation": 0,
                    "placed": False,
                }
            )
        return ts

    def _build_ui(self):
        tabs = QTabWidget()
        # Operate tab
        op = QWidget()
        v = QVBoxLayout(op)
        self.status = QLabel("Ready")
        v.addWidget(self.status)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        v.addWidget(self.log)
        btns = QHBoxLayout()
        b1 = QPushButton("Optimize Placement")
        b1.clicked.connect(self._opt_place)
        b2 = QPushButton("Optimize Feeders")
        b2.clicked.connect(self._opt_feeders)
        b3 = QPushButton("Plan S-Curve Path")
        b3.clicked.connect(self._plan)
        for b in (b1, b2, b3):
            btns.addWidget(b)
        v.addLayout(btns)
        tabs.addTab(op, "Operate")

        # CV tab
        cvtab = QWidget()
        cvl = QVBoxLayout(cvtab)
        cvl.addWidget(QLabel("Computer Vision: orientation & alignment (demo)"))
        self.cvout = QTextEdit()
        self.cvout.setReadOnly(True)
        cvl.addWidget(self.cvout)
        tabs.addTab(cvtab, "Vision")

        # Sim tab
        simtab = QWidget()
        sl = QVBoxLayout(simtab)
        self.simlabel = QLabel("Sim: pos=(0,0) z=80")
        sl.addWidget(self.simlabel)
        tabs.addTab(simtab, "Simulation")

        self.setCentralWidget(tabs)

    def _log(self, msg):
        self.log.append(msg)

    def _opt_place(self):
        self.targets = optimize_placement(self.targets, start=(0.0, 0.0))
        self._log(f"Placement optimized: {len(self.targets)} targets")
        self.status.setText("Placement optimized")

    def _opt_feeders(self):
        feeders = [
            {"type": "0402", "count": 100},
            {"type": "0603", "count": 80},
            {"type": "0805", "count": 60},
        ]
        new = optimize_feeders(self.targets, feeders)
        self._log(f"Feeders optimized: {new}")
        self.status.setText("Feeders optimized")

    def _plan(self):
        wps = np.array([(t["x"], t["z"]) for t in self.targets[:8]])
        segs = plan_path(wps, v_max=200, a_max=100, j_max=500, dt=0.01)
        self._log(
            f"S-curve planned: {len(segs)} segments, {sum(len(s['t']) for s in segs)} samples"
        )
        self.status.setText("Path planned")

    def _tick(self):
        self.sim.step(0.033, target_pos=(50, 30), target_z=20)
        self.simlabel.setText(
            f"Sim: pos=({self.sim.pos[0]:.1f},{self.sim.pos[1]:.1f}) z={self.sim.nozzle_z:.1f}"
        )


def main():
    if not _QT:
        print("PyQt5 not available (missing libGL). Use web GUI: python -m pnp.webgui")
        return
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
