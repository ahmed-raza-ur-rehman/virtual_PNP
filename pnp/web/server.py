"""Complete web server with all endpoints."""
from __future__ import annotations

import http.server
import json
import os

import numpy as np

from pnp.core.history import RunHistory
from pnp.optimization.feeding import optimize_feeders, optimize_turntable
from pnp.optimization.placement import optimize_placement
from pnp.planning.trajectory import plan_path
from pnp.reporting.report import generate_run_report
from pnp.vision.pipeline import orientation_angle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def do_GET(self):
        if self.path == "/api/status":
            self._json({"status": "ok", "version": "2.1.0"})
        elif self.path == "/api/history":
            h = RunHistory()
            self._json({"runs": h.recent(20)})
        else:
            super().do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else "{}"
        try:
            data = json.loads(body)
        except (ValueError, json.JSONDecodeError):
            data = {}
        if self.path == "/api/optimize/placement":
            targets = data.get("targets", [])
            out = optimize_placement(targets)
            self._json({"targets": out})
        elif self.path == "/api/optimize/feeders":
            targets = data.get("targets", [])
            feeders = data.get("feeders", [])
            out = optimize_feeders(targets, feeders)
            self._json({"feeders": out})
        elif self.path == "/api/optimize/tray":
            targets = data.get("targets", [])
            slots = data.get("slots", 12)
            out = optimize_turntable(targets, slots)
            self._json({"slots": out})
        elif self.path == "/api/plan/path":
            wps = np.array(data.get("waypoints", []), dtype=float)
            segs = plan_path(wps) if len(wps) > 1 else []
            self._json({"segments": len(segs), "samples": int(sum(len(s["t"]) for s in segs))})
        elif self.path == "/api/vision/orientation":
            img = np.array(data.get("image", []), dtype=np.uint8)
            if img.size == 0:
                self._json({"angle": 0.0})
            else:
                self._json({"angle": orientation_angle(img)})
        elif self.path == "/api/report":
            path = data.get("path", "report.md")
            generate_run_report(path, data.get("data", {}))
            self._json({"path": path})
        else:
            self.send_error(404)

    def _json(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


def main(port=8000):
    httpd = http.server.HTTPServer(("0.0.0.0", port), Handler)
    print(f"Web server: http://0.0.0.0:{port}/")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
