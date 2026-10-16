"""Lightweight web GUI server exposing Python algorithms and the 3D simulator."""

import http.server
import json
import os

import numpy as np

from pnp.algorithms.path_planning import plan_path
from pnp.algorithms.placement_optimizer import optimize_placement

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else "{}"
        try:
            data = json.loads(body)
        except (ValueError, json.JSONDecodeError):
            data = {}
        if self.path == "/api/optimize_placement":
            targets = data.get("targets", [])
            out = optimize_placement(targets, start=(0.0, 0.0))
            self._json({"targets": out})
        elif self.path == "/api/plan_path":
            wps = np.array(data.get("waypoints", []), dtype=float)
            segs = plan_path(wps) if len(wps) > 1 else []
            self._json({"segments": len(segs), "samples": int(sum(len(s["t"]) for s in segs))})
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
    print(f"Web GUI: http://0.0.0.0:{port}/ (simulator at /b.html)")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
