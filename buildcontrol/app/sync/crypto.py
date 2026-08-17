"""Optional payload encryption for public message brokers.

A free public MQTT broker is readable by anyone who guesses the topic, so the
change payloads can be sealed with a shared passphrase before they leave the
device. AES-256-GCM with a PBKDF2 key derived from the workspace key as salt —
every installation of the same workspace derives the same key from the same
passphrase, no key exchange required.
"""

from __future__ import annotations

import base64
import json
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MARKER = "a256gcm"
ITERATIONS = 200_000
NONCE_BYTES = 12


class DecryptionError(Exception):
    """Raised when a payload cannot be opened with the configured passphrase."""


def derive_key(passphrase: str, salt: str) -> bytes:
    """Derive the 32-byte content key from a passphrase and the workspace key."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt.encode("utf-8"),
        iterations=ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt(body: dict, key: bytes) -> bytes:
    """Seal a change envelope; returns the bytes to publish."""
    nonce = os.urandom(NONCE_BYTES)
    plaintext = json.dumps(body, ensure_ascii=False).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    envelope = {
        "enc": MARKER,
        "n": base64.b64encode(nonce).decode("ascii"),
        "c": base64.b64encode(ciphertext).decode("ascii"),
    }
    return json.dumps(envelope).encode("utf-8")


def decrypt(raw: bytes, key: bytes | None) -> dict:
    """Open a payload, transparently passing through unencrypted ones."""
    body = json.loads(raw.decode("utf-8"))
    if not isinstance(body, dict) or body.get("enc") != MARKER:
        return body
    if key is None:
        raise DecryptionError("payload is encrypted but no passphrase is configured")
    try:
        nonce = base64.b64decode(body["n"])
        ciphertext = base64.b64decode(body["c"])
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    except Exception as exc:  # invalid key, tampering, truncation
        raise DecryptionError("wrong passphrase or damaged payload") from exc
    return json.loads(plaintext.decode("utf-8"))
