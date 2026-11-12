"""Bearer token: birinchi ishga tushishda yaratiladi, ma'lumotlar papkasida saqlanadi."""

import asyncio
import hmac
import os
import secrets
from pathlib import Path

MIN_TOKEN_LENGTH = 32
_BEARER_PREFIX = "bearer "
# SYSTEM va Administrators — xizmat rejimi va tiklash uchun.
_ALWAYS_ALLOWED_SIDS = ("*S-1-5-18", "*S-1-5-32-544")


class AuthError(RuntimeError):
    """Token fayli yaroqsiz."""


def load_or_create_token(token_file: Path) -> tuple[str, bool]:
    """Tokenni qaytaradi; ikkinchi qiymat — hozir yaratilganmi."""
    if token_file.exists():
        token = token_file.read_text(encoding="ascii").strip()
        if len(token) < MIN_TOKEN_LENGTH:
            raise AuthError(
                f"{token_file} yaroqsiz (juda qisqa). Faylni o'chirsangiz, yangi token yaratiladi."
            )
        return token, False
    token = secrets.token_urlsafe(32)
    token_file.write_text(token + "\n", encoding="ascii")
    return token, True


def _icacls_path() -> Path:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")  # noqa: SIM112 — Windows nomi
    return Path(system_root) / "System32" / "icacls.exe"


def _current_account() -> str | None:
    user = os.environ.get("USERNAME", "")
    if not user:
        return None
    domain = os.environ.get("USERDOMAIN", "")
    return f"{domain}\\{user}" if domain else user


async def restrict_to_owner(path: Path) -> bool:
    """Faylga faqat joriy foydalanuvchi, SYSTEM va Administrators kira oladigan qiladi.

    Merosiy ruxsatlarni olib tashlaydi. Muvaffaqiyatli bo'lsa `True`.
    """
    icacls, account = _icacls_path(), _current_account()
    if account is None or not icacls.is_file():
        return False
    grants = [f"{who}:F" for who in (account, *_ALWAYS_ALLOWED_SIDS)]
    process = await asyncio.create_subprocess_exec(
        str(icacls),
        str(path),
        "/inheritance:r",
        "/grant:r",
        *grants,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    return await process.wait() == 0


class TokenAuth:
    """`Authorization: Bearer <token>` sarlavhasini doimiy vaqtda tekshiradi."""

    def __init__(self, token: str) -> None:
        self._token = token.encode("ascii")

    def verify_header(self, header: str | None) -> bool:
        if header is None or not header.lower().startswith(_BEARER_PREFIX):
            return False
        presented = header[len(_BEARER_PREFIX) :].strip().encode("utf-8", "replace")
        return hmac.compare_digest(presented, self._token)
