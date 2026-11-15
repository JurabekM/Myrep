"""Ro'yxatdan o'tish, kirish, sessiya va xavfsizlik jurnali.

Himoya choralari:
- parol faqat `PasswordHasher` xeshi ko'rinishida saqlanadi;
- xato kirishda sabab aytilmaydi (login yoki parol — bitta umumiy xabar) va
  mavjud bo'lmagan login uchun ham xesh hisoblanadi, shunda javob vaqti
  login bor-yo'qligini oshkor qilmaydi;
- ketma-ket xato urinishlar hisobni o'sib boruvchi muddatga qulflaydi;
- sessiya faqat xotirada yashaydi (diskka token yozilmaydi) va harakatsizlik
  muddatidan keyin tugaydi;
- jurnalga parol ham, tanilmagan login matni ham yozilmaydi (odamlar ba'zan
  login maydoniga parolini terib yuboradi).
"""

from __future__ import annotations

import secrets
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from .errors import AccountLocked, AuthError, SessionExpired, ValidationError
from .security import PasswordHasher
from .validation import (
    PASSWORD_MAX,
    normalize_password,
    normalize_username,
    validate_new_password,
)

MAX_FAILED_ATTEMPTS = 5
LOCK_BASE_SECONDS = 30.0
LOCK_MAX_SECONDS = 15 * 60.0
IDLE_TIMEOUT_SECONDS = 15 * 60.0

_GENERIC_LOGIN_ERROR = "Login yoki parol noto'g'ri."

EVENT_LABELS = {
    "register": "Ro'yxatdan o'tildi",
    "login_ok": "Tizimga kirildi",
    "login_failed": "Xato parol bilan kirishga urinish",
    "login_unknown": "Noma'lum login bilan kirishga urinish",
    "login_blocked": "Qulflangan hisobga kirishga urinish",
    "account_locked": "Hisob vaqtincha qulflandi",
    "logout": "Tizimdan chiqildi",
    "session_expired": "Sessiya muddati tugadi",
    "password_changed": "Parol o'zgartirildi",
    "password_change_failed": "Parolni o'zgartirishda joriy parol xato kiritildi",
}


@dataclass
class Session:
    """Tizimga kirgan foydalanuvchi. Faqat jarayon xotirasida mavjud."""

    user_id: int
    username: str
    last_seen: float
    active: bool = True
    password_failures: int = 0


@dataclass(frozen=True)
class AuditEvent:
    at: str
    event: str
    detail: str

    @property
    def label(self) -> str:
        return EVENT_LABELS.get(self.event, self.event)


def lock_duration(failed_attempts: int) -> float:
    """Qulf muddati: 5-xatoda 30 s, har keyingi xatoda ikki baravar, ko'pi bilan 15 daqiqa."""
    extra = max(0, failed_attempts - MAX_FAILED_ATTEMPTS)
    return min(LOCK_BASE_SECONDS * (2 ** min(extra, 16)), LOCK_MAX_SECONDS)


class AuthService:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        hasher: PasswordHasher | None = None,
        clock: Callable[[], float] = time.time,
        idle_timeout: float = IDLE_TIMEOUT_SECONDS,
    ) -> None:
        self._conn = conn
        self._hasher = hasher or PasswordHasher()
        self._clock = clock
        self._idle_timeout = idle_timeout
        self._decoy_hash: str | None = None

    # --- ichki yordamchilar -------------------------------------------------

    def _now_iso(self) -> str:
        stamp = datetime.fromtimestamp(self._clock(), tz=timezone.utc)
        return stamp.isoformat(timespec="seconds")

    def _audit(self, user_id: int | None, event: str, detail: str = "") -> None:
        self._conn.execute(
            "INSERT INTO audit_log (at, user_id, event, detail) VALUES (?, ?, ?, ?)",
            (self._now_iso(), user_id, event, detail),
        )

    def _decoy(self) -> str:
        """Mavjud bo'lmagan login uchun tekshiriladigan soxta xesh (bir marta yaratiladi)."""
        if self._decoy_hash is None:
            self._decoy_hash = self._hasher.hash(secrets.token_urlsafe(24))
        return self._decoy_hash

    # --- ro'yxatdan o'tish ---------------------------------------------------

    def register(self, username: object, password: object) -> int:
        name = normalize_username(username)
        pw = validate_new_password(password, name)
        password_hash = self._hasher.hash(pw)
        try:
            with self._conn:
                cursor = self._conn.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (name, password_hash, self._now_iso()),
                )
                user_id = int(cursor.lastrowid)
                self._audit(user_id, "register")
        except sqlite3.IntegrityError:
            raise ValidationError("Bu login band. Boshqasini tanlang.", "username") from None
        return user_id

    # --- kirish ---------------------------------------------------------------

    def login(self, username: object, password: object) -> Session:
        if not isinstance(password, str) or not isinstance(username, str):
            raise AuthError(_GENERIC_LOGIN_ERROR)
        if len(password) > PASSWORD_MAX:
            # Juda uzun kirishni xeshlamaymiz; bunday parol ro'yxatdan o'ta olmaydi.
            raise AuthError(_GENERIC_LOGIN_ERROR)
        # Soxta xesh login tekshirilishidan OLDIN tayyorlanadi: aks holda uni
        # yaratish vaqti "bunday login yo'q" degan signal bo'lib qolardi.
        decoy = self._decoy()
        try:
            name: str | None = normalize_username(username)
        except ValidationError:
            name = None

        row = None
        if name is not None:
            row = self._conn.execute(
                "SELECT id, username, password_hash, failed_attempts, locked_until "
                "FROM users WHERE username = ?",
                (name,),
            ).fetchone()
        if row is None:
            # Mavjud login bilan bir xil ish: bitta xesh tekshiruvi va bitta jurnal yozuvi.
            # Kiritilgan login matni yozilmaydi (u parol bo'lib chiqishi mumkin).
            self._hasher.verify(password, decoy)
            with self._conn:
                self._audit(None, "login_unknown")
            raise AuthError(_GENERIC_LOGIN_ERROR)

        now = self._clock()
        user_id = int(row["id"])
        locked_until = row["locked_until"]
        if locked_until is not None and now < locked_until:
            # Qulf paytida parol tekshirilmaydi: qulf hujumchiga "sinov" bermaydi.
            with self._conn:
                self._audit(user_id, "login_blocked")
            raise AccountLocked(locked_until - now)

        if not self._hasher.verify(password, row["password_hash"]):
            attempts = int(row["failed_attempts"]) + 1
            lock_for = lock_duration(attempts) if attempts >= MAX_FAILED_ATTEMPTS else 0.0
            with self._conn:
                self._conn.execute(
                    "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                    (attempts, now + lock_for if lock_for else None, user_id),
                )
                self._audit(user_id, "login_failed", f"urinish: {attempts}")
                if lock_for:
                    self._audit(user_id, "account_locked", f"{int(lock_for)} soniya")
            if lock_for:
                raise AccountLocked(lock_for)
            raise AuthError(_GENERIC_LOGIN_ERROR)

        with self._conn:
            new_hash = None
            if self._hasher.needs_rehash(row["password_hash"]):
                # Parametrlar kuchaytirilgan: ochiq parol qo'lda turgan yagona payt.
                new_hash = self._hasher.hash(password)
            self._conn.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = NULL, "
                "password_hash = COALESCE(?, password_hash) WHERE id = ?",
                (new_hash, user_id),
            )
            self._audit(user_id, "login_ok")
        return Session(user_id=user_id, username=row["username"], last_seen=now)

    # --- sessiya ---------------------------------------------------------------

    def require(self, session: Session) -> Session:
        """Sessiya amalda ekanini tekshiradi va faollik vaqtini yangilaydi."""
        if not session.active:
            raise SessionExpired()
        now = self._clock()
        if now - session.last_seen > self._idle_timeout:
            session.active = False
            with self._conn:
                self._audit(session.user_id, "session_expired")
            raise SessionExpired()
        session.last_seen = now
        return session

    def is_expired(self, session: Session) -> bool:
        """Faollik vaqtini yangilamasdan tekshiradi (interfeys taymeri uchun)."""
        return not session.active or self._clock() - session.last_seen > self._idle_timeout

    def logout(self, session: Session) -> None:
        if not session.active:
            return
        session.active = False
        with self._conn:
            self._audit(session.user_id, "logout")

    # --- parolni o'zgartirish ---------------------------------------------------

    def change_password(
        self, session: Session, current_password: object, new_password: object
    ) -> None:
        self.require(session)
        row = self._conn.execute(
            "SELECT password_hash FROM users WHERE id = ?", (session.user_id,)
        ).fetchone()
        current_ok = (
            row is not None
            and isinstance(current_password, str)
            and len(current_password) <= PASSWORD_MAX
            and self._hasher.verify(current_password, row["password_hash"])
        )
        if not current_ok:
            session.password_failures += 1
            with self._conn:
                self._audit(session.user_id, "password_change_failed")
            if session.password_failures >= MAX_FAILED_ATTEMPTS:
                # Ochiq qolgan sessiyada parolni taxmin qilishga yo'l qo'ymaymiz:
                # sessiya yopiladi, qayta kirishda esa qulflash qoidasi ishlaydi.
                self.logout(session)
                raise SessionExpired()
            raise AuthError("Joriy parol noto'g'ri.")
        session.password_failures = 0
        pw = validate_new_password(new_password, session.username)
        if pw == normalize_password(current_password):
            raise ValidationError("Yangi parol joriy paroldan farq qilishi kerak.", "password")
        with self._conn:
            self._conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (self._hasher.hash(pw), session.user_id),
            )
            self._audit(session.user_id, "password_changed")

    # --- jurnal ------------------------------------------------------------------

    def audit_events(self, session: Session, limit: int = 20) -> list[AuditEvent]:
        """Faqat joriy foydalanuvchining o'z hodisalari, eng yangisi birinchi."""
        self.require(session)
        limit = max(1, min(int(limit), 200))
        rows = self._conn.execute(
            "SELECT at, event, detail FROM audit_log WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (session.user_id, limit),
        ).fetchall()
        return [AuditEvent(r["at"], r["event"], r["detail"]) for r in rows]
