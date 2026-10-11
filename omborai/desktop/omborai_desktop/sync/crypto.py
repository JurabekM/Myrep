"""Protokol v2 kriptografiyasi: konvert (AES-256-GCM, mavzu HKDF orqali), canonical JSON va Ed25519 imzo.

Protokol: docs/sync-mqtt.md (2, 4, 5-bo'limlar). Mobil (Dart) bilan bir xil baytlar hosil qilinishi shart.
"""

import base64
import json
import os
from typing import Any

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

KEY_BYTES = 32
PROTOCOL_VERSION = 2
TOPIC_PREFIX = "omborai/v2"


class DecryptionError(Exception):
    """Xabar buzilgan, boshqa kalit bilan shifrlangan yoki shakli noto'g'ri."""


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


def canonical_bytes(op: dict[str, Any]) -> bytes:
    """Imzo uchun baytlar: `sig` siz, kalitlari saralangan, bo'shliqsiz JSON (UTF-8)."""
    body = {key: value for key, value in op.items() if key != "sig"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_op(op: dict[str, Any], public_key_hex: str) -> bool:
    """Operatsiya imzosi shu ochiq kalit bilan to'g'rimi."""
    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public_key.verify(base64.b64decode(op["sig"]), canonical_bytes(op))
    except (InvalidSignature, ValueError, KeyError, TypeError):
        return False
    return True


def seal(key: bytes, message: dict[str, Any], topic: str) -> bytes:
    _check_key(key)
    nonce = os.urandom(12)
    plaintext = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode()
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, topic.encode())
    envelope = {
        "v": PROTOCOL_VERSION,
        "n": base64.b64encode(nonce).decode(),
        "c": base64.b64encode(ciphertext).decode(),
    }
    return json.dumps(envelope).encode()


def open_envelope(key: bytes, raw: bytes, topic: str) -> dict[str, Any]:
    """Konvertni ochadi. Har qanday xato (JSON, versiya, GCM, tur) DecryptionError bo'ladi."""
    _check_key(key)
    try:
        envelope = json.loads(raw)
        if not isinstance(envelope, dict) or envelope.get("v") != PROTOCOL_VERSION:
            raise DecryptionError("Noma'lum protokol versiyasi")
        nonce = base64.b64decode(envelope["n"])
        ciphertext = base64.b64decode(envelope["c"])
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, topic.encode())
        message = json.loads(plaintext)
    except (ValueError, KeyError, TypeError, AttributeError, InvalidTag) as exc:
        raise DecryptionError("Xabarni ochib bo'lmadi") from exc
    if not isinstance(message, dict):
        raise DecryptionError("Xabar ob'ekt emas")
    return message
