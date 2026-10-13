"""Which documents have been uploaded and which vector ids belong to each (SQLite)."""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone

from .models import DocumentInfo


class Registry:
    def __init__(self, path: str):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("""CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, filename TEXT NOT NULL, pages INTEGER NOT NULL, chunks INTEGER NOT NULL,
            chunk_ids TEXT NOT NULL, created_at TEXT NOT NULL)""")
        self._db.commit()

    def save(self, doc: DocumentInfo) -> None:
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO documents VALUES (?, ?, ?, ?, ?, ?)",
                             (doc.id, doc.filename, doc.pages, doc.chunks, json.dumps(doc.chunk_ids), doc.created_at))
            self._db.commit()

    def get(self, doc_id: str) -> DocumentInfo | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return self._row(row) if row else None

    def all(self) -> list[DocumentInfo]:
        with self._lock:
            rows = self._db.execute("SELECT * FROM documents ORDER BY created_at DESC, filename").fetchall()
        return [self._row(r) for r in rows]

    def delete(self, doc_id: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            self._db.commit()

    @staticmethod
    def _row(r) -> DocumentInfo:
        return DocumentInfo(r[0], r[1], r[2], r[3], r[5], json.loads(r[4]))

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
