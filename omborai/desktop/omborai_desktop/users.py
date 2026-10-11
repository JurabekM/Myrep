"""Foydalanuvchilar (login/parol hisoblari) boshqaruvi. Faqat egasi qurilmasi (protokol: docs/sync-mqtt.md).

Har bir o'zgarish `user` operatsiyasi sifatida qaytariladi: chaqiruvchi uni apply va yuboradi.
"""

import uuid
from typing import Any

from . import auth
from .offline.store import LocalStore
from .sync import ops as o

ROLE_OWNER = o.ROLE_OWNER
ROLE_CASHIER = o.ROLE_CASHIER
MIN_PASSWORD = 8


class UserError(ValueError):
    """Foydalanuvchini qo'shish yoki o'zgartirish mumkin emas (xabar foydalanuvchiga ko'rsatiladi)."""


def add_cashier(local: LocalStore, name: str, login: str, password: str) -> dict[str, Any]:
    name = name.strip()
    login = auth.normalize_login(login)
    store_id = local.get_state("store_id") or ""
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
    return local.new_op(o.USER, user)


def set_active(local: LocalStore, user_id: str, active: bool) -> dict[str, Any]:
    row = local.get_user(user_id)
    if row is None or row["store_id"] != local.get_state("store_id"):
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
    return local.new_op(o.USER, user)
