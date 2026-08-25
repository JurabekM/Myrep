"""Maxfiy material uchun at-rest himoya.

Qurilmaning maxfiy kalitlari (ML-DSA-65 sign key, epoch root secret) bazada
OCHIQ saqlanmaydi. Windows'da operatsion tizimning o'z mexanizmi — DPAPI
(`CryptProtectData`) ishlatiladi: kalit foydalanuvchi profiliga bog'lanadi,
boshqa foydalanuvchi yoki boshqa mashina uni ocholmaydi.

DPAPI mavjud bo'lmasa (Linux/macOS yoki xizmat konteksti), ilova **jim
davom etmaydi**: `AllowInsecureKeyStorage` aniq yoqilishi kerak va bu
holat diagnostikada «himoyalanmagan» deb ko'rsatiladi.
"""

from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from dataclasses import dataclass
from typing import ClassVar, Protocol

from distribos.aether_q.vendor import kdf


class SecretStoreError(RuntimeError):
    """Sirni o'rash yoki ochish muvaffaqiyatsiz."""


class SecretStore(Protocol):
    """Sirni o'rash (wrap) va ochish (unwrap) chegarasi."""

    name: str
    is_os_protected: bool

    def wrap(self, plaintext: bytes, context: bytes = b"") -> bytes: ...

    def unwrap(self, wrapped: bytes, context: bytes = b"") -> bytes: ...


# --- Windows DPAPI --------------------------------------------------------


class _DataBlob(ctypes.Structure):
    # `ctypes.Structure` bu maydonni maxsus qoidaga ko'ra o'qiydi —
    # ClassVar FAQAT tip yozuvi, ishga ta'sir qilmaydi.
    _fields_: ClassVar = [
        ("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))
    ]


def _blob(data: bytes) -> _DataBlob:
    buffer = ctypes.create_string_buffer(data, len(data))
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))


def _blob_bytes(blob: _DataBlob) -> bytes:
    return ctypes.string_at(blob.pbData, blob.cbData)


#: DPAPI bayrog'i: mashinaga emas, foydalanuvchi profiliga bog'lash.
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


@dataclass
class WindowsDpapiSecretStore:
    """Windows DPAPI orqali himoya. Kalit OS'da, bizda emas."""

    name: str = "windows-dpapi"
    is_os_protected: bool = True

    def __post_init__(self) -> None:
        if sys.platform != "win32":
            raise SecretStoreError("DPAPI faqat Windows'da mavjud")
        self._crypt32 = ctypes.windll.crypt32  # type: ignore[attr-defined]
        self._kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

    def wrap(self, plaintext: bytes, context: bytes = b"") -> bytes:
        data_in = _blob(plaintext)
        entropy = _blob(context) if context else None
        data_out = _DataBlob()
        ok = self._crypt32.CryptProtectData(
            ctypes.byref(data_in), None,
            ctypes.byref(entropy) if entropy else None,
            None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(data_out),
        )
        if not ok:
            raise SecretStoreError(
                f"CryptProtectData muvaffaqiyatsiz (kod {ctypes.get_last_error()})"
            )
        try:
            return _blob_bytes(data_out)
        finally:
            self._kernel32.LocalFree(data_out.pbData)

    def unwrap(self, wrapped: bytes, context: bytes = b"") -> bytes:
        data_in = _blob(wrapped)
        entropy = _blob(context) if context else None
        data_out = _DataBlob()
        ok = self._crypt32.CryptUnprotectData(
            ctypes.byref(data_in), None,
            ctypes.byref(entropy) if entropy else None,
            None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(data_out),
        )
        if not ok:
            raise SecretStoreError(
                "CryptUnprotectData muvaffaqiyatsiz — sir boshqa foydalanuvchi "
                "yoki boshqa kompyuterda yaratilgan bo'lishi mumkin"
            )
        try:
            return _blob_bytes(data_out)
        finally:
            self._kernel32.LocalFree(data_out.pbData)


# --- Test/portativ variant ------------------------------------------------


@dataclass
class PassphraseSecretStore:
    """Parol asosidagi o'rash — DPAPI yo'q platformalar va testlar uchun.

    ⚠ Bu OS himoyasi EMAS: kalit parolga bog'liq, parol esa ilova
    xotirasida bo'ladi. Diagnostikada `is_os_protected=False` ko'rinadi va
    `PRIVATE_PRODUCTION` profilida ogohlantirish beriladi.
    """

    passphrase: bytes
    name: str = "passphrase"
    is_os_protected: bool = False

    def _key(self, context: bytes) -> bytes:
        prk = kdf.hkdf_extract(b"DistribOS/secret-store/v1", self.passphrase)
        return kdf.hkdf_expand(prk, b"wrap" + context, 32)

    def wrap(self, plaintext: bytes, context: bytes = b"") -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

        nonce = os.urandom(12)
        aead = ChaCha20Poly1305(self._key(context))
        return nonce + aead.encrypt(nonce, plaintext, context)

    def unwrap(self, wrapped: bytes, context: bytes = b"") -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

        if len(wrapped) < 12 + 16:
            raise SecretStoreError("o'ralgan sir juda qisqa")
        nonce, ciphertext = wrapped[:12], wrapped[12:]
        try:
            return ChaCha20Poly1305(self._key(context)).decrypt(nonce, ciphertext, context)
        except Exception as exc:
            raise SecretStoreError("sir ochilmadi") from exc


def default_secret_store(*, allow_insecure: bool = False) -> SecretStore:
    """Platformaga mos eng kuchli variantni tanlaydi.

    Windows'da DPAPI. Boshqa joyda — `allow_insecure=True` bo'lmasa xato.
    """
    if sys.platform == "win32":
        try:
            return WindowsDpapiSecretStore()
        except SecretStoreError:
            pass

    if not allow_insecure:
        raise SecretStoreError(
            "Bu platformada OS darajasidagi kalit himoyasi topilmadi. "
            "Sirlarni himoyasiz saqlash uchun `allow_insecure=True` ni "
            "ataylab yoqing — bu diagnostikada ko'rsatiladi."
        )

    machine = (os.environ.get("COMPUTERNAME") or os.uname().nodename).encode()
    user = (os.environ.get("USERNAME") or os.environ.get("USER") or "").encode()
    return PassphraseSecretStore(passphrase=machine + b"/" + user)
