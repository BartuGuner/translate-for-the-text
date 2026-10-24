"""Favorites stored in userdata/user.db."""
from __future__ import annotations

import csv
import io
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

MAX_CONTEXT = 300
SCHEMA = """
CREATE TABLE IF NOT EXISTS favorite (
  id       INTEGER PRIMARY KEY,
  lemma    TEXT NOT NULL UNIQUE,
  word     TEXT NOT NULL,
  pos      TEXT,
  meanings TEXT NOT NULL,
  context  TEXT,
  added_at TEXT NOT NULL
);
"""
COLUMNS = ("id", "lemma", "word", "pos", "meanings", "context", "added_at")


class Favorites:
    def __init__(self, path: Path) -> None:
        self._path = path

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._path)
        try:
            conn.execute(SCHEMA)
            yield conn
            conn.commit()
        finally:
            conn.close()

    def add(self, word: str, lemma: str, pos: str | None, meanings: list[str],
            context: str | None) -> tuple[dict, bool]:
        """Insert a favorite. Returns (row, created); existing lemma is returned unchanged."""
        ctx = context.strip()[:MAX_CONTEXT] if context else None
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO favorite (lemma, word, pos, meanings, context, added_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (lemma, word, pos, json.dumps(meanings, ensure_ascii=False), ctx, now),
            )
            created = cur.rowcount == 1
            row = conn.execute(f"SELECT {', '.join(COLUMNS)} FROM favorite WHERE lemma = ?", (lemma,)).fetchone()
        return to_dict(row), created

    def list(self, query: str = "") -> list[dict]:
        sql = f"SELECT {', '.join(COLUMNS)} FROM favorite"
        params: tuple = ()
        if query:
            sql += " WHERE word LIKE ? OR lemma LIKE ? OR meanings LIKE ?"
            like = f"%{query}%"
            params = (like, like, like)
        with self._conn() as conn:
            rows = conn.execute(sql + " ORDER BY added_at DESC, id DESC", params).fetchall()
        return [to_dict(r) for r in rows]

    def delete(self, fav_id: int) -> bool:
        with self._conn() as conn:
            return conn.execute("DELETE FROM favorite WHERE id = ?", (fav_id,)).rowcount == 1

    def export_csv(self) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["word", "lemma", "pos", "meanings", "context", "added_at"])
        for f in self.list():
            writer.writerow([f["word"], f["lemma"], f["pos"] or "", "; ".join(f["meanings"]),
                             f["context"] or "", f["added_at"]])
        return "\ufeff" + buf.getvalue()


def to_dict(row: tuple) -> dict:
    fav = dict(zip(COLUMNS, row))
    fav["meanings"] = json.loads(fav["meanings"])
    return fav
