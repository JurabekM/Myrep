"""Do'kon kaliti bilan shifrlash: AES-256-GCM, mavzu nomi HKDF orqali."""

import base64
import json
import os
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

KEY_BYTES = 32
TOPIC_PREFIX = "omborai/v1"


class DecryptionError(Exception):
    """Xabar buzilgan yoki boshqa kalit bilan shifrlangan."""


def generate_store_key() -> bytes:
    return os.urandom(KEY_BYTES)


def _check_key(key: bytes) -> None:
    if len(key) != KEY_BYTES:
        raise ValueError("Do'kon kaliti 32 bayt bo'lishi kerak")


def topic_for(key: bytes) -> str:
    """Kalitdan olinadigan mavzu. Kalitsiz uni taxmin qilib bo'lmaydi."""
    _check_key(key)
    digest = HKDF(algorithm=hashes.SHA256(), length=16, salt=None, info=b"topic").derive(key)
    return f"{TOPIC_PREFIX}/{digest.hex()}/ops"


def seal(key: bytes, message: dict[str, Any], topic: str) -> bytes:
    _check_key(key)
    nonce = os.urandom(12)
    plaintext = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode()
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, topic.encode())
    envelope = {
        "v": 1,
        "n": base64.b64encode(nonce).decode(),
        "c": base64.b64encode(ciphertext).decode(),
    }
    return json.dumps(envelope).encode()


def open_envelope(key: bytes, raw: bytes, topic: str) -> dict[str, Any]:
    _check_key(key)
    try:
        envelope = json.loads(raw)
        if envelope.get("v") != 1:
            raise DecryptionError("Noma'lum protokol versiyasi")
        nonce = base64.b64decode(envelope["n"])
        ciphertext = base64.b64decode(envelope["c"])
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, topic.encode())
    except (ValueError, KeyError, TypeError, InvalidTag) as exc:
        raise DecryptionError("Xabarni ochib bo'lmadi") from exc
    return json.loads(plaintext)
