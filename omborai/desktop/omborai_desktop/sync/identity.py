"""Qurilma kaliti (Ed25519): har bir operatsiyani shu qurilma imzolaydi. docs/sync-mqtt.md, 2-bo'lim."""

import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

SEED_BYTES = 32


class DeviceIdentity:
    def __init__(self, seed: bytes) -> None:
        if len(seed) != SEED_BYTES:
            raise ValueError("Qurilma kaliti 32 bayt bo'lishi kerak")
        self._key = Ed25519PrivateKey.from_private_bytes(seed)
        raw = self._key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.public_key_hex = raw.hex()

    @classmethod
    def generate(cls) -> "DeviceIdentity":
        return cls(os.urandom(SEED_BYTES))

    def sign(self, data: bytes) -> bytes:
        return self._key.sign(data)
