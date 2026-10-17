"""GDSII writer (simplified)."""
import struct
import typing


class GDSIIWriter:
    def __init__(self):
        self.records: list[bytes] = []

    def header(self, version: int = 600):
        self.records.append(struct.pack(">HH", 0x0002, version))

    def begin_structure(self, name: str):
        name_bytes = name.encode().ljust(32, b"\x00")
        self.records.append(b"STRNAME" + name_bytes)

    def add_boundary(self, layer: int, datatype: int, points: list[typing.Tuple[int, int]]):
        self.records.append(struct.pack(">HH", layer, datatype))
        for x, y in points:
            self.records.append(struct.pack(">ii", x, y))

    def end_structure(self):
        self.records.append(b"ENDSTR")

    def write(self, path: str):
        with open(path, "wb") as f:
            self.header()
            f.writelines(self.records)
            f.write(b"ENDLIB")

    def report(self) -> str:
        return f"GDSII: {len(self.records)} records"
