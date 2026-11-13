"""Fayllar indeksi: SQLite + FTS5 (trigram) — nom ichidan qidirish, har qanday alifboda.

Sinxron kod; `FilesService` uni bitta ishchi oqimda chaqiradi (ulanish o'sha oqimda ochiladi).
"""

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    root INTEGER NOT NULL,
    relpath TEXT NOT NULL COLLATE NOCASE,
    name TEXT NOT NULL,
    ext TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime REAL NOT NULL,
    is_dir INTEGER NOT NULL,
    gen INTEGER NOT NULL,
    UNIQUE (root, relpath)
);
CREATE INDEX IF NOT EXISTS files_ext ON files (ext);
CREATE VIRTUAL TABLE IF NOT EXISTS names USING fts5 (name, tokenize = 'trigram');
CREATE TABLE IF NOT EXISTS trash (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    root INTEGER NOT NULL,
    relpath TEXT NOT NULL,
    name TEXT NOT NULL,
    size INTEGER NOT NULL,
    is_dir INTEGER NOT NULL,
    deleted_ts REAL NOT NULL
);
"""
# Trigram indeks kamida 3 belgili so'rovni talab qiladi; qisqasi uchun LIKE.
MIN_MATCH_CHARS = 3
_FILE_COLUMNS = "f.root, f.relpath, f.name, f.ext, f.size, f.mtime, f.is_dir"


@dataclass(frozen=True, slots=True)
class Entry:
    root: int
    relpath: str  # ildizga nisbatan, '/' bilan
    name: str
    ext: str  # kichik harfda, nuqtasiz
    size: int
    mtime: float
    is_dir: bool

    def as_dict(self) -> dict[str, Any]:
        folder = self.relpath.rsplit("/", 1)[0] if "/" in self.relpath else ""
        return {
            "root": self.root,
            "path": self.relpath,
            "name": self.name,
            "folder": folder,
            "ext": self.ext,
            "size": None if self.is_dir else self.size,
            "mtime": self.mtime,
            "is_dir": self.is_dir,
        }


@dataclass(frozen=True, slots=True)
class TrashItem:
    id: int
    root: int
    relpath: str
    name: str
    size: int
    is_dir: bool
    deleted_ts: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "root": self.root,
            "path": self.relpath,
            "name": self.name,
            "size": self.size,
            "is_dir": self.is_dir,
            "deleted": self.deleted_ts,
        }


def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class FileIndex:
    def __init__(self, db_file: Path) -> None:
        self._db = sqlite3.connect(db_file)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.executescript(SCHEMA)
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    # --- yozish -------------------------------------------------------------
    def upsert_many(self, entries: Iterable[Entry], gen: int) -> int:
        """Yozuvlarni qo'shadi yoki yangilaydi; `gen` — skanerlash avlodi."""
        count = 0
        for entry in entries:
            row = self._db.execute(
                "SELECT id FROM files WHERE root = ? AND relpath = ?", (entry.root, entry.relpath)
            ).fetchone()
            if row is None:
                cursor = self._db.execute(
                    "INSERT INTO files (root, relpath, name, ext, size, mtime, is_dir, gen) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        entry.root,
                        entry.relpath,
                        entry.name,
                        entry.ext,
                        entry.size,
                        entry.mtime,
                        entry.is_dir,
                        gen,
                    ),
                )
                self._db.execute(
                    "INSERT INTO names (rowid, name) VALUES (?, ?)", (cursor.lastrowid, entry.name)
                )
            else:
                self._db.execute(
                    "UPDATE files SET size = ?, mtime = ?, is_dir = ?, gen = ? WHERE id = ?",
                    (entry.size, entry.mtime, entry.is_dir, gen, row[0]),
                )
            count += 1
        self._db.commit()
        return count

    def _delete_ids(self, ids: list[int]) -> int:
        for start in range(0, len(ids), 500):
            chunk = ids[start : start + 500]
            marks = ",".join("?" * len(chunk))
            self._db.execute(f"DELETE FROM names WHERE rowid IN ({marks})", chunk)  # noqa: S608
            self._db.execute(f"DELETE FROM files WHERE id IN ({marks})", chunk)  # noqa: S608
        self._db.commit()
        return len(ids)

    def delete_path(self, root: int, relpath: str) -> int:
        """Yozuvni va (papka bo'lsa) ichidagi hamma narsani o'chiradi."""
        rows = self._db.execute(
            "SELECT id FROM files WHERE root = ? AND (relpath = ? OR relpath LIKE ? ESCAPE '\\')",
            (root, relpath, _like_escape(relpath) + "/%"),
        ).fetchall()
        return self._delete_ids([row[0] for row in rows])

    def drop_stale(self, root: int, gen: int) -> int:
        """To'liq skanerlashdan keyin: bu avlodda uchramagan yozuvlarni o'chiradi."""
        rows = self._db.execute(
            "SELECT id FROM files WHERE root = ? AND gen < ?", (root, gen)
        ).fetchall()
        return self._delete_ids([row[0] for row in rows])

    def drop_other_roots(self, root_count: int) -> int:
        """Manifestdan olib tashlangan ildizlarning yozuvlarini o'chiradi."""
        rows = self._db.execute("SELECT id FROM files WHERE root >= ?", (root_count,)).fetchall()
        return self._delete_ids([row[0] for row in rows])

    # --- o'qish -------------------------------------------------------------
    def contains(self, root: int, relpath: str) -> bool:
        row = self._db.execute(
            "SELECT 1 FROM files WHERE root = ? AND relpath = ?", (root, relpath)
        ).fetchone()
        return row is not None

    def max_gen(self) -> int:
        row = self._db.execute("SELECT COALESCE(MAX(gen), 0) FROM files").fetchone()
        return int(row[0])

    def counts(self) -> tuple[int, int]:
        """(fayllar, papkalar)."""
        row = self._db.execute(
            "SELECT COALESCE(SUM(is_dir = 0), 0), COALESCE(SUM(is_dir = 1), 0) FROM files"
        ).fetchone()
        return int(row[0]), int(row[1])

    def count_by_root(self) -> dict[int, int]:
        rows = self._db.execute(
            "SELECT root, COUNT(*) FROM files WHERE is_dir = 0 GROUP BY root"
        ).fetchall()
        return {int(root): int(count) for root, count in rows}

    def search(
        self,
        query: str = "",
        *,
        ext: str = "",
        root: int | None = None,
        min_size: int | None = None,
        max_size: int | None = None,
        limit: int = 100,
    ) -> list[Entry]:
        """Nom ichidan qidiradi (katta-kichik harf farqsiz). Bo'sh so'rov — filtrlar bo'yicha."""
        tables, where, args = "files f", ["1 = 1"], list[Any]()
        text = query.strip()
        if len(text) >= MIN_MATCH_CHARS:
            tables = "names n JOIN files f ON f.id = n.rowid"
            where.append("names MATCH ?")
            args.append('"' + text.replace('"', '""') + '"')
        elif text:
            where.append("f.name LIKE ? ESCAPE '\\'")
            args.append("%" + _like_escape(text) + "%")
        if ext.strip():
            where.append("f.ext = ?")
            args.append(ext.strip().lstrip(".").lower())
        if root is not None:
            where.append("f.root = ?")
            args.append(root)
        if min_size is not None:
            where.append("f.is_dir = 0 AND f.size >= ?")
            args.append(min_size)
        if max_size is not None:
            where.append("f.is_dir = 0 AND f.size <= ?")
            args.append(max_size)
        sql = (
            f"SELECT {_FILE_COLUMNS} FROM {tables} WHERE {' AND '.join(where)} "  # noqa: S608
            "ORDER BY f.is_dir DESC, f.name COLLATE NOCASE, f.relpath LIMIT ?"
        )
        rows = self._db.execute(sql, [*args, limit]).fetchall()
        return [Entry(r[0], r[1], r[2], r[3], r[4], r[5], bool(r[6])) for r in rows]

    # --- savat --------------------------------------------------------------
    def trash_add(self, entry: Entry, deleted_ts: float) -> int:
        cursor = self._db.execute(
            "INSERT INTO trash (root, relpath, name, size, is_dir, deleted_ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (entry.root, entry.relpath, entry.name, entry.size, entry.is_dir, deleted_ts),
        )
        self._db.commit()
        return int(cursor.lastrowid or 0)

    def trash_list(self) -> list[TrashItem]:
        rows = self._db.execute(
            "SELECT id, root, relpath, name, size, is_dir, deleted_ts FROM trash ORDER BY id DESC"
        ).fetchall()
        return [TrashItem(r[0], r[1], r[2], r[3], r[4], bool(r[5]), r[6]) for r in rows]

    def trash_get(self, trash_id: int) -> TrashItem | None:
        return next((item for item in self.trash_list() if item.id == trash_id), None)

    def trash_remove(self, trash_id: int) -> None:
        self._db.execute("DELETE FROM trash WHERE id = ?", (trash_id,))
        self._db.commit()
