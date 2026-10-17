"""Layout vs Schematic (LVS) check."""
from __future__ import annotations


class LVS:
    def __init__(self):
        self.errors: list[str] = []

    def extract_netlist(self, layout: dict) -> dict[str, set[str]]:
        """Extract connectivity from layout."""
        nets: dict[str, set[str]] = {}
        for shape in layout.get("shapes", []):
            net = shape.get("net", "unconnected")
            if net not in nets:
                nets[net] = set()
            nets[net].add(shape.get("name", ""))
        return nets

    def compare(self, schematic: dict[str, set[str]], layout: dict[str, set[str]]) -> list[str]:
        errors = []
        # check all schematic nets exist in layout
        for net, pins in schematic.items():
            if net not in layout:
                errors.append(f"Net {net} missing in layout")
            elif pins != layout[net]:
                errors.append(f"Net {net} mismatch: schematic={pins}, layout={layout[net]}")
        # check extra nets in layout
        for net in layout:
            if net not in schematic:
                errors.append(f"Extra net {net} in layout")
        self.errors = errors
        return errors

    def run(self, schematic: dict, layout: dict) -> list[str]:
        sch_nets = self.extract_netlist(schematic)
        lay_nets = self.extract_netlist(layout)
        return self.compare(sch_nets, lay_nets)

    def report(self) -> str:
        if not self.errors:
            return "LVS: PASS"
        return "LVS: FAIL\n" + "\n".join(f"  - {e}" for e in self.errors)
