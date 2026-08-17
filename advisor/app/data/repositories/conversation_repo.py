"""Suhbat va xabar repozitoriylari."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.data.database import Database


@dataclass
class Conversation:
    id: int
    title: str
    module: str
    model: str | None
    summary: str | None
    message_count: int
    created_at: str
    updated_at: str


@dataclass
class Message:
    id: int
    conversation_id: int
    role: str
    content: str
    sources: list[dict] = field(default_factory=list)
    confidence: float | None = None
    category: str | None = None
    model: str | None = None
    feedback: int | None = None
    created_at: str = ""


def _to_conversation(row) -> Conversation:
    return Conversation(
        id=row["id"], title=row["title"], module=row["module"], model=row["model"],
        summary=row["summary"], message_count=row["message_count"],
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


def _to_message(row) -> Message:
    return Message(
        id=row["id"], conversation_id=row["conversation_id"], role=row["role"],
        content=row["content"],
        sources=json.loads(row["sources"]) if row["sources"] else [],
        confidence=row["confidence"], category=row["category"], model=row["model"],
        feedback=row["feedback"], created_at=row["created_at"],
    )


class ConversationRepository:
    def __init__(self, db: Database):
        self._db = db

    def create(self, title: str, module: str = "chat", model: str | None = None) -> Conversation:
        conn = self._db.connection()
        with conn:
            cur = conn.execute(
                "INSERT INTO conversations (title, module, model) VALUES (?, ?, ?)",
                (title[:120], module, model),
            )
        return self.get(cur.lastrowid)  # type: ignore[arg-type]

    def get(self, conversation_id: int) -> Conversation | None:
        row = self._db.connection().execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return _to_conversation(row) if row else None

    def list_recent(self, limit: int = 50) -> list[Conversation]:
        rows = self._db.connection().execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_to_conversation(r) for r in rows]

    def update_summary(self, conversation_id: int, summary: str) -> None:
        conn = self._db.connection()
        with conn:
            conn.execute(
                "UPDATE conversations SET summary = ?, updated_at = datetime('now') WHERE id = ?",
                (summary, conversation_id),
            )

    def touch(self, conversation_id: int, message_delta: int = 0) -> None:
        conn = self._db.connection()
        with conn:
            conn.execute(
                "UPDATE conversations SET message_count = message_count + ?, "
                "updated_at = datetime('now') WHERE id = ?",
                (message_delta, conversation_id),
            )

    def delete(self, conversation_id: int) -> None:
        conn = self._db.connection()
        with conn:
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))


class MessageRepository:
    def __init__(self, db: Database):
        self._db = db

    def add(
        self,
        conversation_id: int,
        role: str,
        content: str,
        *,
        sources: list[dict] | None = None,
        confidence: float | None = None,
        category: str | None = None,
        model: str | None = None,
    ) -> Message:
        conn = self._db.connection()
        with conn:
            cur = conn.execute(
                "INSERT INTO messages (conversation_id, role, content, sources, "
                "confidence, category, model) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    conversation_id, role, content,
                    json.dumps(sources, ensure_ascii=False) if sources else None,
                    confidence, category, model,
                ),
            )
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _to_message(row)

    def list_for_conversation(self, conversation_id: int, limit: int = 200) -> list[Message]:
        rows = self._db.connection().execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
        return [_to_message(r) for r in rows]

    def recent_history(self, conversation_id: int, limit: int = 12) -> list[Message]:
        rows = self._db.connection().execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
        return [_to_message(r) for r in reversed(rows)]

    def set_feedback(self, message_id: int, feedback: int) -> None:
        conn = self._db.connection()
        with conn:
            conn.execute(
                "UPDATE messages SET feedback = ? WHERE id = ?", (feedback, message_id)
            )
