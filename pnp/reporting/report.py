"""Report generation."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ReportSection:
    title: str
    content: str
    level: int = 1


class ReportGenerator:
    def __init__(self, title: str = "Report"):
        self.title = title
        self.sections: list[ReportSection] = []
        self.metadata: dict[str, Any] = {}
        self.created_at = datetime.now()

    def add_section(self, title: str, content: str, level: int = 1):
        self.sections.append(ReportSection(title=title, content=content, level=level))

    def add_table(self, title: str, headers: list[str], rows: list[list[Any]]):
        lines = [f"## {title}", ""]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in rows:
            lines.append("| " + " | ".join(str(c) for c in row) + " |")
        self.add_section(title, "\n".join(lines))

    def add_chart_data(self, title: str, data: dict[str, list[float]], chart_type: str = "line"):
        content = f"Chart: {chart_type}\n" + json.dumps(data)
        self.add_section(title, content)

    def render_markdown(self) -> str:
        lines = [f"# {self.title}", ""]
        lines.append(f"Generated: {self.created_at.isoformat()}")
        lines.append("")
        for s in self.sections:
            prefix = "#" * (s.level + 1)
            lines.append(f"{prefix} {s.title}")
            lines.append("")
            lines.append(s.content)
            lines.append("")
        return "\n".join(lines)

    def render_html(self) -> str:
        html = f"<html><head><title>{self.title}</title></head><body>"
        html += f"<h1>{self.title}</h1>"
        html += f"<p>Generated: {self.created_at.isoformat()}</p>"
        for s in self.sections:
            html += f"<h{s.level+1}>{s.title}</h{s.level+1}>"
            html += f"<pre>{s.content}</pre>"
        html += "</body></html>"
        return html

    def save(self, path: str, format: str = "markdown"):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if format == "markdown":
            with open(path, "w") as f:
                f.write(self.render_markdown())
        elif format == "html":
            with open(path, "w") as f:
                f.write(self.render_html())
        elif format == "json":
            with open(path, "w") as f:
                json.dump({"title": self.title, "sections": [{"title": s.title, "content": s.content} for s in self.sections]}, f, indent=2)

    def generate_run_report(self, path: str, data: dict[str, Any]):
        rg = ReportGenerator(title="Pick-and-Place Run Report")
        rg.metadata = data
        rg.add_section("Summary", f"Run completed at {datetime.now().isoformat()}")
        for k, v in data.items():
            rg.add_section(k, str(v))
        if "placement" in data:
            rg.add_section("Placement", str(data["placement"]))
        if "metrics" in data:
            rg.add_table("Metrics", ["Metric", "Value"], [[k, v] for k, v in data["metrics"].items()])
        rg.save(path)


def generate_run_report(path: str, data: dict[str, Any]):
    rg = ReportGenerator()
    rg.generate_run_report(path, data)
