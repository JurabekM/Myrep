"""Foydalanuvchilar (kassirlar) boshqaruvi: qo'shish va faollashtirish/o'chirish. Faqat do'kon egasi.

Har bir o'zgarish `user` operatsiyasi sifatida qaytariladi (LWW): chaqiruvchi uni apply va yuboradi.
"""

import uuid
from typing import Any

from . import auth
from .offline.store import LocalStore
from .sync import ops as o

ROLE_OWNER = "owner"
ROLE_CASHIER = "cashier"
MIN_PASSWORD = 8


class UserError(ValueError):
    """Foydalanuvchini qo'shish yoki o'zgartirish mumkin emas (xabar foydalanuvchiga ko'rsatiladi)."""


def add_cashier(
    local: LocalStore, store_id: str, device_id: str, name: str, login: str, password: str
) -> dict[str, Any]:
    name = name.strip()
    login = auth.normalize_login(login)
    if not name or not login:
        raise UserError("Ism va loginni kiriting")
    if len(password) < MIN_PASSWORD:
        raise UserError(f"Parol kamida {MIN_PASSWORD} belgi bo'lsin")
    if local.login_exists(store_id, login):
        raise UserError("Bu login band")
    salt, pw_hash = auth.hash_password(password)
    user = {
        "id": str(uuid.uuid4()),
        "login": login,
        "name": name,
        "role": ROLE_CASHIER,
        "salt": salt,
        "pw_hash": pw_hash,
        "active": True,
    }
    return o.new_op(o.USER, store_id, user, device_id=device_id)


def set_active(
    local: LocalStore, store_id: str, device_id: str, user_id: str, active: bool
) -> dict[str, Any]:
    row = local.get_user(user_id)
    if row is None or row["store_id"] != store_id:
        raise UserError("Foydalanuvchi topilmadi")
    if row["role"] == ROLE_OWNER:
        raise UserError("Do'kon egasini o'chirib bo'lmaydi")
    user = {
        "id": row["id"],
        "login": row["login"],
        "name": row["name"],
        "role": row["role"],
        "salt": row["salt"],
        "pw_hash": row["pw_hash"],
        "active": active,
    }
    return o.new_op(o.USER, store_id, user, device_id=device_id)
