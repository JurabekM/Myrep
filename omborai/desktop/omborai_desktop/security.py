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
