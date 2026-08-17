"""Jadval sxemalari va idempotent migratsiya.

Migratsiyalar ``schema_version`` jadvali orqali kuzatiladi; ``migrate`` har
ishga tushishda chaqirilishi xavfsiz — faqat qo'llanilmagan qadamlar bajariladi.
"""

from __future__ import annotations

from app.core.logging_setup import get_logger
from app.data.database import Database

logger = get_logger(__name__)

# Har bir element — (versiya, SQL). Faqat qo'shiladi, tahrirlangan migratsiya
# qayta ishlatilmaydi.
_MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            module TEXT NOT NULL DEFAULT 'chat',
            model TEXT,
            summary TEXT,
            message_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sources TEXT,           -- JSON list
            confidence REAL,
            category TEXT,
            model TEXT,
            feedback INTEGER,       -- 1 / -1 / NULL
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS ix_messages_conv ON messages(conversation_id, id);

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            content_type TEXT,
            size INTEGER NOT NULL DEFAULT 0,
            extracted_text TEXT,
            status TEXT NOT NULL DEFAULT 'pending',  -- pending/ready/failed
            error TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS kb_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection TEXT NOT NULL,        -- 'legal' | 'knowledge' | 'user_doc'
            source_id TEXT NOT NULL,         -- hujjat/qonun identifikatori
            title TEXT,
            url TEXT,
            article TEXT,                    -- qonun moddasi
            chunk_index INTEGER NOT NULL DEFAULT 0,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS ix_kb_collection ON kb_chunks(collection);
        CREATE INDEX IF NOT EXISTS ix_kb_source ON kb_chunks(source_id);

        CREATE TABLE IF NOT EXISTS usage_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            module TEXT NOT NULL,
            provider TEXT NOT NULL,
            requests INTEGER NOT NULL DEFAULT 0,
            tokens INTEGER NOT NULL DEFAULT 0,
            UNIQUE(day, module, provider)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """,
    ),
]


def migrate(db: Database) -> int:
    conn = db.connection()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"
    )
    conn.commit()
    row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    current = row["v"] or 0

    applied = 0
    for version, sql in _MIGRATIONS:
        if version <= current:
            continue
        logger.info("Migratsiya qo'llanmoqda: v%d", version)
        with conn:
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
        applied += 1
    return applied
