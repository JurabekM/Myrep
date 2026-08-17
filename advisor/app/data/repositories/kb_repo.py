"""Bilimlar bazasi (RAG chunklari) va foydalanish statistikasi repozitoriylari."""

from __future__ import annotations

from dataclasses import dataclass

from app.data.database import Database


@dataclass
class KBChunk:
    id: int
    collection: str
    source_id: str
    title: str | None
    url: str | None
    article: str | None
    chunk_index: int
    text: str


def _to_chunk(row) -> KBChunk:
    return KBChunk(
        id=row["id"], collection=row["collection"], source_id=row["source_id"],
        title=row["title"], url=row["url"], article=row["article"],
        chunk_index=row["chunk_index"], text=row["text"],
    )


class KBRepository:
    def __init__(self, db: Database):
        self._db = db

    def add_chunks(
        self,
        collection: str,
        source_id: str,
        chunks: list[dict],
        *,
        title: str | None = None,
        url: str | None = None,
    ) -> int:
        """chunks: [{"text":..., "article":..., "chunk_index":...}, ...]"""
        conn = self._db.connection()
        with conn:
            conn.execute(
                "DELETE FROM kb_chunks WHERE collection = ? AND source_id = ?",
                (collection, source_id),
            )
            conn.executemany(
                "INSERT INTO kb_chunks (collection, source_id, title, url, article, "
                "chunk_index, text) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        collection, source_id, title, url,
                        c.get("article"), c.get("chunk_index", i), c["text"],
                    )
                    for i, c in enumerate(chunks)
                ],
            )
        return len(chunks)

    def get_collection(self, collection: str) -> list[KBChunk]:
        rows = self._db.connection().execute(
            "SELECT * FROM kb_chunks WHERE collection = ? ORDER BY id ASC", (collection,)
        ).fetchall()
        return [_to_chunk(r) for r in rows]

    def count(self, collection: str) -> int:
        row = self._db.connection().execute(
            "SELECT COUNT(*) AS c FROM kb_chunks WHERE collection = ?", (collection,)
        ).fetchone()
        return row["c"]

    def list_sources(self, collection: str) -> list[dict]:
        rows = self._db.connection().execute(
            "SELECT source_id, title, url, COUNT(*) AS chunks "
            "FROM kb_chunks WHERE collection = ? GROUP BY source_id ORDER BY MAX(id) DESC",
            (collection,),
        ).fetchall()
        return [dict(r) for r in rows]


class UsageRepository:
    def __init__(self, db: Database):
        self._db = db

    def record(self, day: str, module: str, provider: str, tokens: int = 0) -> None:
        conn = self._db.connection()
        with conn:
            conn.execute(
                "INSERT INTO usage_stats (day, module, provider, requests, tokens) "
                "VALUES (?, ?, ?, 1, ?) "
                "ON CONFLICT(day, module, provider) DO UPDATE SET "
                "requests = requests + 1, tokens = tokens + excluded.tokens",
                (day, module, provider, tokens),
            )

    def by_day(self, days: int = 30) -> list[dict]:
        rows = self._db.connection().execute(
            "SELECT day, SUM(requests) AS requests, SUM(tokens) AS tokens "
            "FROM usage_stats GROUP BY day ORDER BY day DESC LIMIT ?", (days,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def by_module(self) -> list[dict]:
        rows = self._db.connection().execute(
            "SELECT module, SUM(requests) AS requests FROM usage_stats "
            "GROUP BY module ORDER BY requests DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def by_provider(self) -> list[dict]:
        rows = self._db.connection().execute(
            "SELECT provider, SUM(requests) AS requests FROM usage_stats "
            "GROUP BY provider ORDER BY requests DESC"
        ).fetchall()
        return [dict(r) for r in rows]
