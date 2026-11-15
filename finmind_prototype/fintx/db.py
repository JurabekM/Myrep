"""SQLite ombori: fayl joylashuvi, ruxsatlar va sxema.

Barcha so'rovlar parametrlangan (`?`), foydalanuvchi matni hech qachon SQL
satriga qo'shilmaydi. Sxemadagi CHECK cheklovlari xizmat qatlamidagi
tekshiruvlarni takrorlaydi: kod xato qilsa ham bazaga noto'g'ri qator tushmaydi.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

from .errors import FinTxError
from .money import MAX_AMOUNT_MINOR
from .validation import NOTE_MAX

APP_DIR_NAME = "FinTx"
DB_FILE_NAME = "fintx.db"
ENV_DB_PATH = "FINTX_DB"
SCHEMA_VERSION = 1
MEMORY = ":memory:"

_SCHEMA = f"""
CREATE TABLE users (
    id              INTEGER PRIMARY KEY,
    username        TEXT    NOT NULL UNIQUE
                            CHECK (length(username) BETWEEN 3 AND 32),
    password_hash   TEXT    NOT NULL CHECK (length(password_hash) > 0),
    created_at      TEXT    NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
    locked_until    REAL
);

CREATE TABLE transactions (
    id           INTEGER PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind         TEXT    NOT NULL CHECK (kind IN ('income', 'expense')),
    amount_minor INTEGER NOT NULL
                         CHECK (typeof(amount_minor) = 'integer'
                                AND amount_minor > 0
                                AND amount_minor <= {MAX_AMOUNT_MINOR}),
    category     TEXT    NOT NULL CHECK (length(category) BETWEEN 1 AND 40),
    note         TEXT    NOT NULL DEFAULT '' CHECK (length(note) <= {NOTE_MAX}),
    occurred_on  TEXT    NOT NULL
                         CHECK (occurred_on GLOB
                                '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    created_at   TEXT    NOT NULL
);

CREATE INDEX idx_transactions_user_date
    ON transactions (user_id, occurred_on DESC, id DESC);

CREATE TABLE audit_log (
    id      INTEGER PRIMARY KEY,
    at      TEXT    NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    event   TEXT    NOT NULL,
    detail  TEXT    NOT NULL DEFAULT ''
);

CREATE INDEX idx_audit_user ON audit_log (user_id, id DESC);
"""


def default_db_path() -> Path:
    """Foydalanuvchining shaxsiy ma'lumotlar papkasidagi baza yo'li."""
    override = os.environ.get(ENV_DB_PATH)
    if override:
        return Path(override).expanduser()
    home = Path.home()
    if sys.platform == "darwin":
        base = home / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA") or home / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    return base / APP_DIR_NAME / DB_FILE_NAME


def _prepare_file(path: Path) -> None:
    """Baza faylini faqat egasi o'qiy oladigan qilib yaratadi (POSIX: 0600).

    Windows'da %APPDATA% ACL'lari sukut bo'yicha faqat shu foydalanuvchiga
    ochiq; u yerda `chmod` ma'noga ega emas.
    """
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            # Fayl avvaldan kengroq ruxsat bilan mavjud bo'lsa — toraytiramiz.
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)


def connect(path: str | os.PathLike[str] | None = None) -> sqlite3.Connection:
    """Bazaga ulanadi va sxemani tayyorlaydi. `":memory:"` — testlar uchun."""
    target = str(path) if path is not None else str(default_db_path())
    if target != MEMORY:
        _prepare_file(Path(target))
    conn = sqlite3.connect(target)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        # O'chirilgan qatorlar diskda nol bilan ustidan yoziladi.
        conn.execute("PRAGMA secure_delete = ON")
        _migrate(conn)
    except sqlite3.DatabaseError:
        conn.close()
        raise FinTxError(
            "Ma'lumotlar bazasini ochib bo'lmadi: fayl buzilgan yoki boshqa formatda."
        ) from None
    except BaseException:
        conn.close()
        raise
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version == SCHEMA_VERSION:
        return
    if version > SCHEMA_VERSION:
        raise FinTxError("Ma'lumotlar bazasi dasturning yangiroq versiyasida yaratilgan.")
    # executescript o'zi COMMIT qiladi; bo'sh bazada bir marta bajariladi.
    conn.executescript(f"BEGIN;\n{_SCHEMA}\nPRAGMA user_version = {SCHEMA_VERSION};\nCOMMIT;")
