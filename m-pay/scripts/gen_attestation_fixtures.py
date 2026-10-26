#!/usr/bin/env python3
"""Attestatsiya tekshiruvchisi uchun test fiksturasi: RSA-2048 ildiz → P-384 oraliq → P-256 leaf.

Haqiqiy Android zanjirlariga o'xshash tuzilma (Google RSA-4096 / ECDSA P-384 ildizlari) — Rust
tekshiruvchisining RSA-SHA256 va ECDSA-SHA384 yo'llarini sinash uchun. Barcha kalitlar TEST uchun.

    python scripts/gen_attestation_fixtures.py crates/mpay-pqlink/tests/data/attest_rsa_p384.json
"""

import datetime as dt
import json
import sys

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import NameOID

KEY_DESCRIPTION_OID = x509.ObjectIdentifier("1.3.6.1.4.1.11129.2.1.17")


def tlv(tag: int, value: bytes) -> bytes:
    n = len(value)
    if n < 0x80:
        ln = bytes([n])
    elif n < 0x100:
        ln = bytes([0x81, n])
    else:
        ln = bytes([0x82, n >> 8, n & 0xFF])
    return bytes([tag]) + ln + value


def key_description(level: int, challenge: bytes) -> bytes:
    body = (
        tlv(0x02, bytes([0x01, 0x2C]))
        + tlv(0x0A, bytes([level]))
        + tlv(0x02, bytes([0x01, 0x2C]))
        + tlv(0x0A, bytes([level]))
        + tlv(0x04, challenge)
        + tlv(0x04, b"")
        + tlv(0x30, b"")
        + tlv(0x30, root_of_trust())
    )
    return tlv(0x30, body)


def root_of_trust() -> bytes:
    """hardwareEnforced.rootOfTrust [704]: Verified, deviceLocked = true (BER teg BF 85 40)."""
    rot = tlv(0x04, bytes(32)) + tlv(0x01, bytes([0xFF])) + tlv(0x0A, bytes([0x00])) + tlv(0x04, bytes(32))
    seq = tlv(0x30, rot)
    return bytes([0xBF, 0x85, 0x40, len(seq)]) + seq


def name(cn: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def cert(subject, issuer, pub, signer, algo, ca: bool, ext=None):
    b = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(pub)
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc))
        .not_valid_after(dt.datetime(2045, 1, 1, tzinfo=dt.timezone.utc))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
    )
    if ext is not None:
        b = b.add_extension(x509.UnrecognizedExtension(KEY_DESCRIPTION_OID, ext), critical=False)
    return b.sign(signer, algo)


def main() -> None:
    root_k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    inter_k = ec.generate_private_key(ec.SECP384R1())
    leaf_k = ec.generate_private_key(ec.SECP256R1())
    root = cert(name("Test RSA Attestation Root"), name("Test RSA Attestation Root"), root_k.public_key(), root_k, hashes.SHA256(), True)
    inter = cert(name("Test P-384 Intermediate"), root.subject, inter_k.public_key(), root_k, hashes.SHA256(), True)
    leaf = cert(name("Android Keystore Key"), inter.subject, leaf_k.public_key(), inter_k, hashes.SHA384(), False, key_description(2, b"fixture"))
    der = lambda c: c.public_bytes(serialization.Encoding.DER).hex()
    out = {
        "note": "TEST fiksturasi — faqat attestatsiya tekshiruvchisi testlari uchun",
        "chain": [der(leaf), der(inter), der(root)],
        "root": der(root),
        "leaf_pkcs8": leaf_k.private_bytes(
            serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        ).hex(),
    }
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
