"""Command-line interface for Virtual PnP."""
from __future__ import annotations

import json

import numpy as np
import typer
from rich.console import Console
from rich.table import Table

from pnp.optimization.placement import optimize_placement
from pnp.planning.trajectory import plan_path

app = typer.Typer(help="Virtual SMD Pick & Place CLI")
console = Console()


@app.command()
def optimize(input: str = typer.Option(..., "--input", "-i", help="JSON file with targets"),
            output: str = typer.Option("optimized.json", "--output", "-o")):
    with open(input) as f:
        data = json.load(f)
    targets = data["targets"]
    opt = optimize_placement(targets)
    with open(output, "w") as f:
        json.dump({"targets": opt}, f, indent=2)
    console.print(f"[green]Optimized {len(opt)} targets -> {output}[/green]")


@app.command()
def plan(waypoints: str = typer.Option(..., "--waypoints", "-w", help="CSV x,z pairs"),
         v: float = 200.0, a: float = 100.0, j: float = 500.0):
    pts = np.array([[float(x) for x in row.split(",")] for row in waypoints.split(";")])
    segs = plan_path(pts, v_max=v, a_max=a, j_max=j)
    t = Table(title="Trajectory")
    t.add_column("Segment"); t.add_column("Samples"); t.add_column("Duration(s)")
    for i, s in enumerate(segs):
        t.add_row(str(i), str(len(s["t"])), f"{s['t'][-1]:.3f}")
    console.print(t)


@app.command()
def info():
    console.print("[bold]Virtual PnP v2.0.0[/bold] - professional SMD pick-and-place platform")


if __name__ == "__main__":
    app()
