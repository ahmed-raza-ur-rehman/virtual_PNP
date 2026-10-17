"""Parts database for components and feeders."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass
class Part:
    id: str
    name: str
    package: str
    value: str = ""
    manufacturer: str = ""
    mpn: str = ""
    feeder_type: str = "tape"
    feeder_width: float = 8.0
    height: float = 1.0
    polarity: int = 0
    rotation: float = 0.0
    vision_model: str = ""
    pick_height: float = 0.5
    place_height: float = 0.1
    speed_factor: float = 1.0


class PartsDatabase:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS parts (
                id TEXT PRIMARY KEY, name TEXT, package TEXT, value TEXT,
                manufacturer TEXT, mpn TEXT, feeder_type TEXT, feeder_width REAL,
                height REAL, polarity INTEGER, rotation REAL, vision_model TEXT,
                pick_height REAL, place_height REAL, speed_factor REAL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS feeders (
                id TEXT PRIMARY KEY, part_id TEXT, type TEXT, slot INTEGER,
                x REAL, y REAL, z REAL, capacity INTEGER, remaining INTEGER,
                FOREIGN KEY (part_id) REFERENCES parts(id)
            )
        """)
        self.conn.commit()

    def add_part(self, part: Part):
        self.conn.execute("""
            INSERT OR REPLACE INTO parts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (part.id, part.name, part.package, part.value, part.manufacturer, part.mpn,
              part.feeder_type, part.feeder_width, part.height, part.polarity, part.rotation,
              part.vision_model, part.pick_height, part.place_height, part.speed_factor))
        self.conn.commit()

    def get_part(self, part_id: str) -> Part | None:
        row = self.conn.execute("SELECT * FROM parts WHERE id=?", (part_id,)).fetchone()
        if row is None:
            return None
        return Part(*row)

    def list_parts(self, package: str | None = None) -> list[Part]:
        if package:
            rows = self.conn.execute("SELECT * FROM parts WHERE package=?", (package,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM parts").fetchall()
        return [Part(*r) for r in rows]

    def search_parts(self, query: str) -> list[Part]:
        rows = self.conn.execute("SELECT * FROM parts WHERE name LIKE ? OR package LIKE ? OR value LIKE ?",
                                (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
        return [Part(*r) for r in rows]

    def delete_part(self, part_id: str):
        self.conn.execute("DELETE FROM parts WHERE id=?", (part_id,))
        self.conn.commit()

    def add_feeder(self, feeder_id: str, part_id: str, feeder_type: str, slot: int, x: float, y: float, z: float, capacity: int):
        self.conn.execute("INSERT OR REPLACE INTO feeders VALUES (?,?,?,?,?,?,?,?,?)",
                          (feeder_id, part_id, feeder_type, slot, x, y, z, capacity, capacity))
        self.conn.commit()

    def get_feeder(self, feeder_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM feeders WHERE id=?", (feeder_id,)).fetchone()
        if row is None:
            return None
        cols = ["id", "part_id", "type", "slot", "x", "y", "z", "capacity", "remaining"]
        return dict(zip(cols, row))

    def list_feeders(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM feeders").fetchall()
        cols = ["id", "part_id", "type", "slot", "x", "y", "z", "capacity", "remaining"]
        return [dict(zip(cols, r)) for r in rows]

    def consume_feeder(self, feeder_id: str, count: int = 1) -> bool:
        row = self.conn.execute("SELECT remaining FROM feeders WHERE id=?", (feeder_id,)).fetchone()
        if row is None or row[0] < count:
            return False
        self.conn.execute("UPDATE feeders SET remaining = remaining - ? WHERE id=?", (count, feeder_id))
        self.conn.commit()
        return True

    def refill_feeder(self, feeder_id: str, count: int | None = None):
        if count is None:
            self.conn.execute("UPDATE feeders SET remaining = capacity WHERE id=?", (feeder_id,))
        else:
            self.conn.execute("UPDATE feeders SET remaining = remaining + ? WHERE id=?", (count, feeder_id))
        self.conn.commit()

    def get_low_feeders(self, threshold: int = 10) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM feeders WHERE remaining < ?", (threshold,)).fetchall()
        cols = ["id", "part_id", "type", "slot", "x", "y", "z", "capacity", "remaining"]
        return [dict(zip(cols, r)) for r in rows]

    def export_json(self) -> str:
        parts = [p.__dict__ for p in self.list_parts()]
        feeders = self.list_feeders()
        import json
        return json.dumps({"parts": parts, "feeders": feeders}, indent=2)

    def close(self):
        self.conn.close()


class PartsDB:
    def __init__(self, db_path=":memory:"):
        self._db = PartsDatabase(db_path)
        self.path = db_path

    def add_part(self, part_id, name, package, **kwargs):
        part = Part(id=part_id, name=name, package=package, **{k: v for k, v in kwargs.items() if hasattr(Part, k)})
        self._db.add_part(part)

    def get_part(self, part_id):
        part = self._db.get_part(part_id)
        if part is None:
            return None
        return (part.id, part.name, part.package, part.value, part.manufacturer, part.mpn,
                part.feeder_type, part.feeder_width, part.height, part.polarity, part.rotation,
                part.vision_model, part.pick_height, part.place_height, part.speed_factor)

    def list_parts(self):
        return self._db.list_parts()

    def close(self):
        self._db.close()
