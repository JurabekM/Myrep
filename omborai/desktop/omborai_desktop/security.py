"""Lokal baza kaliti.

Kalit OS xavfsiz xotirasida saqlanadi (Windows Credential Manager, macOS Keychain, Linux Secret Service).
Faylda saqlanmaydi. Birinchi ishga tushirishda tasodifiy 256-bitli kalit yaratiladi.
"""

import secrets

import keyring

SERVICE = "omborai-desktop"
ACCOUNT = "local-db-key"


def get_or_create_db_key() -> str:
    key = keyring.get_password(SERVICE, ACCOUNT)
    if key is None:
        key = secrets.token_hex(32)
        keyring.set_password(SERVICE, ACCOUNT, key)
    return key


STORE_KEY_ACCOUNT = "mqtt-store-key"


def get_or_create_store_key() -> bytes:
    """Do'kon kaliti (MQTT shifrlash). Qurilmalar o'rtasida OMBORAI_STORE_KEY (hex) orqali juftlanadi."""
    import os

    from .sync.crypto import generate_store_key

    override = os.environ.get("OMBORAI_STORE_KEY")
    if override:
        return bytes.fromhex(override)
    stored = keyring.get_password(SERVICE, STORE_KEY_ACCOUNT)
    if stored is None:
        key = generate_store_key()
        keyring.set_password(SERVICE, STORE_KEY_ACCOUNT, key.hex())
        return key
    return bytes.fromhex(stored)
