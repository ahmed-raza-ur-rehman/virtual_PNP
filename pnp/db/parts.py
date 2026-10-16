"""Parts and recipe database."""
from __future__ import annotations

import sqlite3


class PartsDB:
    def __init__(self, path: str = "parts.db"):
        self.conn = sqlite3.connect(path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS parts (pn TEXT PRIMARY KEY, name TEXT, package TEXT)")

    def add_part(self, pn, name, package):
        self.conn.execute("INSERT OR REPLACE INTO parts VALUES (?,?,?)", (pn, name, package))
        self.conn.commit()

    def get_part(self, pn):
        cur = self.conn.execute("SELECT * FROM parts WHERE pn=?", (pn,))
        return cur.fetchone()
