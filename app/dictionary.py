"""Read-only access to data/dictionary.db."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

Sense = dict  # {"pos": str, "tr": list[str]}

MAX_SHOWN = 5


class Dictionary:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._local = threading.local()
        self.forms = self._load_forms()

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(f"{self._path.as_uri()}?mode=ro", uri=True, check_same_thread=False)
            self._local.conn = conn
        return conn

    def _load_forms(self) -> dict[str, str]:
        return dict(self._conn().execute("SELECT surface, lemma FROM form"))

    def entry_count(self) -> int:
        return self._conn().execute("SELECT COUNT(*) FROM entry").fetchone()[0]

    def find(self, word: str) -> list[Sense] | None:
        """Senses for a headword (best part of speech first), or None if absent."""
        rows = self._conn().execute(
            "SELECT e.id, e.pos, m.tr FROM entry e JOIN meaning m ON m.entry_id = e.id "
            "WHERE e.word = ? ORDER BY e.rank DESC, e.id, m.ord",
            (word,),
        ).fetchall()
        if not rows:
            return None
        senses: dict[int, Sense] = {}
        for entry_id, pos, tr in rows:
            sense = senses.setdefault(entry_id, {"pos": pos, "tr": []})
            if len(sense["tr"]) < MAX_SHOWN:
                sense["tr"].append(tr)
        return list(senses.values())
