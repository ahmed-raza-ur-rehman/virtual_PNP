"""SQLite-backed run history."""
from __future__ import annotations

import json
import sqlite3
import time


class RunHistory:
    def __init__(self, db_path: str = "pnp_history.db"):
        self.db_path = db_path
        self._init()

    def _init(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                profile TEXT,
                placed INTEGER,
                accuracy REAL,
                cph REAL,
                data TEXT
            )""")

    def record(self, profile: str, placed: int, accuracy: float, cph: float, data: dict | None = None):
        with sqlite3.connect(self.db_path) as c:
            c.execute("INSERT INTO runs (timestamp, profile, placed, accuracy, cph, data) VALUES (?,?,?,?,?,?)",
                      (time.time(), profile, placed, accuracy, cph, json.dumps(data or {})))

    def recent(self, limit: int = 10):
        with sqlite3.connect(self.db_path) as c:
            cur = c.execute("SELECT id, timestamp, profile, placed, accuracy, cph FROM runs ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(zip(["id", "timestamp", "profile", "placed", "accuracy", "cph"], r)) for r in cur.fetchall()]
