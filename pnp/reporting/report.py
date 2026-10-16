"""Report generation (Markdown)."""
from __future__ import annotations

from pathlib import Path


def generate_run_report(path: str, data: dict):
    lines = ["# Run Report", ""]
    for k, v in data.items():
        lines.append(f"- **{k}**: {v}")
    Path(path).write_text("\n".join(lines))
