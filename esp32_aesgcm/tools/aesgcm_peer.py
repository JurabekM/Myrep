#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESP32 dagi `aesgcm` moduli bilan mos PC tomoni (server, skript, test).

Paket formati: nonce (12) | shifrmatn | teg (16).

    pip install cryptography

    python3 tools/aesgcm_peer.py keygen
    python3 tools/aesgcm_peer.py encrypt --key <hex> --aad esp32-01 "SALOM"
    python3 tools/aesgcm_peer.py decrypt --key <hex> --aad esp32-01 <paket_hex>
"""
import argparse
import os
import sys

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_LEN = 12
TAG_LEN = 16


def encrypt(key: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    nonce = os.urandom(NONCE_LEN)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, aad or None)


def decrypt(key: bytes, packet: bytes, aad: bytes = b"") -> bytes:
    if len(packet) < NONCE_LEN + TAG_LEN:
        raise ValueError("paket juda qisqa")
    return AESGCM(key).decrypt(packet[:NONCE_LEN], packet[NONCE_LEN:], aad or None)


def _key(text: str) -> bytes:
    key = bytes.fromhex(text)
    if len(key) != 32:
        raise argparse.ArgumentTypeError("kalit 32 bayt (64 ta hex belgi) bo'lishi kerak")
    return key


def main() -> int:
    parser = argparse.ArgumentParser(description="AES-256-GCM: ESP32 bilan mos paketlar")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("keygen", help="yangi tasodifiy kalit")
    for name in ("encrypt", "decrypt"):
        p = sub.add_parser(name)
        p.add_argument("--key", type=_key, required=True, help="kalit, hex")
        p.add_argument("--aad", default="", help="AAD matni (ESP32 dagi DEVICE_ID)")
        p.add_argument("data", help="ochiq matn (encrypt) yoki paket hex (decrypt)")
    args = parser.parse_args()

    if args.cmd == "keygen":
        key = os.urandom(32)
        print("hex:", key.hex())
        print("secrets.h uchun:")
        for i in range(0, 32, 8):
            print("    " + " ".join(f"0x{b:02x}," for b in key[i:i + 8]))
        return 0

    aad = args.aad.encode()
    if args.cmd == "encrypt":
        print(encrypt(args.key, args.data.encode(), aad).hex())
        return 0

    try:
        print(decrypt(args.key, bytes.fromhex(args.data), aad).decode("utf-8", "replace"))
    except InvalidTag:
        print("XATO: teg mos kelmadi (kalit/AAD noto'g'ri yoki paket o'zgartirilgan)",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
