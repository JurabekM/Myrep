# -*- coding: utf-8 -*-
"""
Autentifikatsiya va foydalanuvchi boshqaruvi servisi.

* Login/logout, sessiyalar (DB da saqlanadi — restartdan keyin ham amal qiladi)
* Hisob blokirovkasi (ketma-ket xato urinishlardan keyin)
* Sessiya timeout (sirg'aluvchi — har faollikda uzayadi)
* Admin foydalanuvchini avtomatik yaratish (birinchi ishga tushishda)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from src.core.logger import get_logger
from src.core.security import (
    check_password_policy,
    generate_password,
    hash_password,
    new_session_token,
    verify_password,
)
from src.core.utils import now_str
from src.auth.rbac import valid_roles

_TS = "%Y-%m-%d %H:%M:%S"


class AuthError(Exception):
    """Autentifikatsiya/avtorizatsiya xatosi (xabari foydalanuvchiga ko'rsatiladi)."""


class AuthService:
    """Foydalanuvchilar, parollar va sessiyalarni boshqaruvchi servis."""

    def __init__(self, db, config, audit) -> None:
        self._db = db
        self._config = config
        self._audit = audit
        self._log = get_logger("auth")

    # ------------------------------------------------------------------ #
    #  Bootstrap: admin yaratish
    # ------------------------------------------------------------------ #

    def ensure_admin(self, data_dir: Path) -> str | None:
        """
        Bazada foydalanuvchi bo'lmasa ``admin`` yaratadi.

        Tasodifiy parol generatsiya qilinadi, konsolga chiqariladi va
        ``data/admin_credentials.txt`` ga yoziladi. Yangi parol yaratilgan
        bo'lsa uni qaytaradi, aks holda None.
        """
        count = int(self._db.scalar("SELECT COUNT(*) FROM users", (), 0) or 0)
        if count > 0:
            return None

        password = generate_password(12)
        self._db.insert("users", {
            "username": "admin",
            "password_hash": hash_password(password),
            "full_name": "Tizim administratori",
            "role": "administrator",
            "is_active": 1,
            "must_change_password": 1,
            "created_at": now_str(),
            "updated_at": now_str(),
        })
        credentials_file = data_dir / "admin_credentials.txt"
        credentials_file.write_text(
            "UzERP — administrator hisobi (birinchi ishga tushishda yaratilgan)\n"
            "===================================================================\n"
            f"Login:  admin\n"
            f"Parol:  {password}\n\n"
            "DIQQAT: tizimga kirgach parolni almashtiring va bu faylni o'chiring!\n",
            encoding="utf-8",
        )
        self._audit.security("user.admin_created", details="Birinchi ishga tushish")
        self._log.info("Admin foydalanuvchi yaratildi (parol: data/admin_credentials.txt)")
        return password

    # ------------------------------------------------------------------ #
    #  Login / Logout / Sessiya
    # ------------------------------------------------------------------ #

    def login(self, username: str, password: str, ip: str = "",
              user_agent: str = "") -> dict:
        """
        Foydalanuvchini tekshiradi va yangi sessiya ochadi.

        :return: ``{"token": ..., "user": {...}}``
        :raises AuthError: login/parol xato, hisob bloklangan yoki nofaol
        """
        username = (username or "").strip().lower()
        user = self._db.query_one(
            "SELECT * FROM users WHERE LOWER(username) = ?", (username,)
        )

        if not user or not int(user.get("is_active") or 0):
            self._audit.security("login.failed", details=f"username={username}", ip=ip)
            raise AuthError("Login yoki parol noto'g'ri.")

        # Blokirovka tekshiruvi
        locked_until = user.get("locked_until")
        if locked_until:
            try:
                if datetime.strptime(locked_until, _TS) > datetime.now():
                    self._audit.security("login.locked", user=user, ip=ip)
                    raise AuthError(
                        "Hisob vaqtincha bloklangan. Birozdan so'ng qayta urinib ko'ring."
                    )
            except ValueError:
                pass  # buzilgan qiymat — e'tiborsiz

        if not verify_password(password or "", user["password_hash"]):
            self._register_failed_attempt(user, ip)
            raise AuthError("Login yoki parol noto'g'ri.")

        # Muvaffaqiyat: hisoblagichlarni tozalash, sessiya ochish
        self._db.update("users", {
            "failed_attempts": 0,
            "locked_until": None,
            "last_login": now_str(),
        }, "id = ?", (user["id"],))

        token = new_session_token()
        timeout = int(self._config.get("security.session_timeout_minutes", 30))
        expires_at = (datetime.now() + timedelta(minutes=timeout)).strftime(_TS)
        self._db.insert("sessions", {
            "token": token,
            "user_id": user["id"],
            "ip": ip,
            "user_agent": (user_agent or "")[:300],
            "created_at": now_str(),
            "expires_at": expires_at,
            "is_active": 1,
        })
        self._audit.security("login.success", user=user, ip=ip)
        return {"token": token, "user": self._public_user(user)}

    def logout(self, token: str) -> None:
        """Sessiyani yopadi."""
        session = self._db.query_one(
            "SELECT s.*, u.username FROM sessions s "
            "JOIN users u ON u.id = s.user_id WHERE s.token = ?", (token,)
        )
        self._db.update("sessions", {"is_active": 0}, "token = ?", (token,))
        if session:
            self._audit.security(
                "logout", user={"id": session["user_id"],
                                "username": session["username"]}
            )

    def validate_session(self, token: str) -> dict | None:
        """
        Sessiya tokenini tekshiradi; amal qilsa foydalanuvchini qaytaradi.

        Sirg'aluvchi timeout: har muvaffaqiyatli tekshiruvda muddat uzayadi.
        """
        if not token:
            return None
        row = self._db.query_one(
            "SELECT s.expires_at, u.* FROM sessions s "
            "JOIN users u ON u.id = s.user_id "
            "WHERE s.token = ? AND s.is_active = 1", (token,)
        )
        if not row:
            return None
        try:
            if datetime.strptime(row["expires_at"], _TS) < datetime.now():
                self._db.update("sessions", {"is_active": 0}, "token = ?", (token,))
                return None
        except (ValueError, TypeError):
            return None
        if not int(row.get("is_active") or 0):
            return None

        timeout = int(self._config.get("security.session_timeout_minutes", 30))
        new_expiry = (datetime.now() + timedelta(minutes=timeout)).strftime(_TS)
        self._db.update("sessions", {"expires_at": new_expiry}, "token = ?", (token,))
        return self._public_user(row)

    def cleanup_expired_sessions(self) -> int:
        """Muddati o'tgan sessiyalarni nofaol qiladi (background worker uchun)."""
        return self._db.update(
            "sessions", {"is_active": 0},
            "is_active = 1 AND expires_at < ?", (now_str(),)
        )

    # ------------------------------------------------------------------ #
    #  Foydalanuvchi boshqaruvi
    # ------------------------------------------------------------------ #

    def create_user(self, actor: dict, username: str, password: str,
                    full_name: str = "", role: str = "guest",
                    email: str = "", phone: str = "") -> int:
        """Yangi foydalanuvchi yaratadi (faqat ``users.manage`` ruxsati bilan)."""
        username = (username or "").strip().lower()
        if not username or len(username) < 3:
            raise AuthError("Login kamida 3 ta belgidan iborat bo'lishi kerak.")
        if role not in valid_roles():
            raise AuthError(f"Noma'lum rol: {role}")
        policy_error = check_password_policy(
            password, int(self._config.get("security.password_min_length", 8))
        )
        if policy_error:
            raise AuthError(policy_error)
        if self._db.query_one("SELECT id FROM users WHERE LOWER(username) = ?",
                              (username,)):
            raise AuthError("Bunday login allaqachon mavjud.")

        user_id = self._db.insert("users", {
            "username": username,
            "password_hash": hash_password(password),
            "full_name": full_name,
            "role": role,
            "email": email,
            "phone": phone,
            "is_active": 1,
            "created_at": now_str(),
            "updated_at": now_str(),
        })
        self._audit.log("user.create", user=actor, entity="user",
                        entity_id=user_id, details=f"{username} ({role})")
        return user_id

    def update_user(self, actor: dict, user_id: int, *, full_name: str | None = None,
                    role: str | None = None, email: str | None = None,
                    phone: str | None = None, is_active: int | None = None) -> bool:
        """Foydalanuvchi ma'lumotlarini yangilaydi."""
        data: dict = {}
        if full_name is not None:
            data["full_name"] = full_name
        if role is not None:
            if role not in valid_roles():
                raise AuthError(f"Noma'lum rol: {role}")
            data["role"] = role
        if email is not None:
            data["email"] = email
        if phone is not None:
            data["phone"] = phone
        if is_active is not None:
            data["is_active"] = int(is_active)
        if not data:
            return False
        data["updated_at"] = now_str()
        affected = self._db.update("users", data, "id = ?", (user_id,))
        self._audit.log("user.update", user=actor, entity="user",
                        entity_id=user_id, details=str(sorted(data.keys())))
        return affected > 0

    def change_password(self, user_id: int, old_password: str,
                        new_password: str) -> None:
        """Foydalanuvchi o'z parolini almashtiradi."""
        user = self._db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user or not verify_password(old_password or "", user["password_hash"]):
            raise AuthError("Joriy parol noto'g'ri.")
        self._set_password(user, new_password)

    def reset_password(self, actor: dict, user_id: int, new_password: str) -> None:
        """Administrator boshqa foydalanuvchi parolini yangilaydi."""
        user = self._db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user:
            raise AuthError("Foydalanuvchi topilmadi.")
        self._set_password(user, new_password, must_change=True)
        self._audit.security("user.password_reset", user=actor,
                             entity="user", entity_id=user_id)

    def list_users(self) -> list[dict]:
        """Barcha foydalanuvchilar (parolsiz, xavfsiz ko'rinishda)."""
        rows = self._db.query(
            "SELECT id, username, full_name, role, email, phone, is_active, "
            "last_login, created_at FROM users ORDER BY id"
        )
        return rows

    # ------------------------------------------------------------------ #
    #  Ichki yordamchilar
    # ------------------------------------------------------------------ #

    def _set_password(self, user: dict, new_password: str,
                      must_change: bool = False) -> None:
        """Parol siyosatini tekshirib, yangi xeshni saqlaydi."""
        policy_error = check_password_policy(
            new_password, int(self._config.get("security.password_min_length", 8))
        )
        if policy_error:
            raise AuthError(policy_error)
        self._db.update("users", {
            "password_hash": hash_password(new_password),
            "must_change_password": 1 if must_change else 0,
            "updated_at": now_str(),
        }, "id = ?", (user["id"],))
        self._audit.security("user.password_changed",
                             user=user, entity="user", entity_id=user["id"])

    def _register_failed_attempt(self, user: dict, ip: str) -> None:
        """Xato urinishni hisoblaydi; chegaradan oshsa hisobni bloklaydi."""
        attempts = int(user.get("failed_attempts") or 0) + 1
        max_attempts = int(self._config.get("security.max_login_attempts", 5))
        data: dict = {"failed_attempts": attempts}
        if attempts >= max_attempts:
            lockout = int(self._config.get("security.lockout_minutes", 15))
            data["locked_until"] = (
                datetime.now() + timedelta(minutes=lockout)
            ).strftime(_TS)
            self._audit.security("account.locked", user=user, ip=ip,
                                 details=f"{attempts} ta xato urinish")
        else:
            self._audit.security("login.failed", user=user, ip=ip,
                                 details=f"urinish #{attempts}")
        self._db.update("users", data, "id = ?", (user["id"],))

    @staticmethod
    def _public_user(row: dict) -> dict:
        """Foydalanuvchining xavfsiz (parolsiz) ko'rinishi."""
        return {
            "id": row["id"],
            "username": row["username"],
            "full_name": row.get("full_name") or "",
            "role": row.get("role") or "guest",
            "email": row.get("email") or "",
            "phone": row.get("phone") or "",
            "must_change_password": int(row.get("must_change_password") or 0),
        }
