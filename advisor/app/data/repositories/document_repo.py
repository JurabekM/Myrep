"""Yuklangan hujjatlar repozitoriysi."""

from __future__ import annotations

from dataclasses import dataclass

from app.data.database import Database


@dataclass
class Document:
    id: int
    filename: str
    path: str
    content_type: str | None
    size: int
    extracted_text: str | None
    status: str
    error: str | None
    created_at: str


def _to_document(row) -> Document:
    return Document(
        id=row["id"], filename=row["filename"], path=row["path"],
        content_type=row["content_type"], size=row["size"],
        extracted_text=row["extracted_text"], status=row["status"],
        error=row["error"], created_at=row["created_at"],
    )


class DocumentRepository:
    def __init__(self, db: Database):
        self._db = db

    def create(self, filename: str, path: str, content_type: str, size: int) -> Document:
        conn = self._db.connection()
        with conn:
            cur = conn.execute(
                "INSERT INTO documents (filename, path, content_type, size, status) "
                "VALUES (?, ?, ?, ?, 'pending')",
                (filename, path, content_type, size),
            )
        return self.get(cur.lastrowid)  # type: ignore[arg-type]

    def get(self, document_id: int) -> Document | None:
        row = self._db.connection().execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        return _to_document(row) if row else None

    def list_all(self, limit: int = 100) -> list[Document]:
        rows = self._db.connection().execute(
            "SELECT * FROM documents ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_to_document(r) for r in rows]

    def mark_ready(self, document_id: int, extracted_text: str) -> None:
        conn = self._db.connection()
        with conn:
            conn.execute(
                "UPDATE documents SET status = 'ready', extracted_text = ?, error = NULL "
                "WHERE id = ?",
                (extracted_text, document_id),
            )

    def mark_failed(self, document_id: int, error: str) -> None:
        conn = self._db.connection()
        with conn:
            conn.execute(
                "UPDATE documents SET status = 'failed', error = ? WHERE id = ?",
                (error[:500], document_id),
            )

    def delete(self, document_id: int) -> None:
        conn = self._db.connection()
        with conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
