"""Design Rule Check (DRC)."""
from __future__ import annotations


class DRC:
    def __init__(self, min_width: float = 0.1, min_spacing: float = 0.1, min_via_enclosure: float = 0.05):
        self.min_width = min_width
        self.min_spacing = min_spacing
        self.min_via_enclosure = min_via_enclosure
        self.violations: list[dict] = []

    def check_width(self, shapes: list[dict]) -> list[dict]:
        viols = []
        for s in shapes:
            if s.get("width", 0) < self.min_width:
                viols.append({"type": "width", "shape": s, "msg": f"width {s['width']} < {self.min_width}"})
        self.violations.extend(viols)
        return viols

    def check_spacing(self, shapes: list[dict]) -> list[dict]:
        viols = []
        for i in range(len(shapes)):
            for j in range(i + 1, len(shapes)):
                s1, s2 = shapes[i], shapes[j]
                dist = abs(s1.get("x", 0) - s2.get("x", 0)) + abs(s1.get("y", 0) - s2.get("y", 0))
                if dist < self.min_spacing and s1.get("layer") == s2.get("layer"):
                    viols.append({"type": "spacing", "shapes": (s1, s2), "msg": f"spacing {dist} < {self.min_spacing}"})
        self.violations.extend(viols)
        return viols

    def check_via_enclosure(self, vias: list[dict], metals: list[dict]) -> list[dict]:
        viols = []
        for v in vias:
            enclosed = False
            for m in metals:
                if (m.get("layer") == v.get("layer") and
                        m.get("x", 0) <= v.get("x", 0) <= m.get("x", 0) + m.get("w", 0) and
                        m.get("y", 0) <= v.get("y", 0) <= m.get("y", 0) + m.get("h", 0)):
                    enclosed = True
                    break
            if not enclosed:
                viols.append({"type": "via_enclosure", "via": v, "msg": "via not enclosed"})
        self.violations.extend(viols)
        return viols

    def run(self, layout: dict) -> list[dict]:
        self.violations = []
        self.check_width(layout.get("shapes", []))
        self.check_spacing(layout.get("shapes", []))
        self.check_via_enclosure(layout.get("vias", []), layout.get("shapes", []))
        return self.violations

    def report(self) -> str:
        if not self.violations:
            return "DRC: PASS (0 violations)"
        lines = [f"DRC: {len(self.violations)} violations"]
        for v in self.violations:
            lines.append(f"  - {v['type']}: {v['msg']}")
        return "\n".join(lines)
