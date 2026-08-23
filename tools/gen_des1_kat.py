"""DES-1 va KDF uchun umumiy test vektorlarini generatsiya qiladi.

Bu **rasmiy AETHER-Q KAT'i EMAS** — bu bizning cross-implementation
moslik testimiz. AETHER-Q ning o'z KAT'i faqat primitivlarni va biz
ishlatmaydigan 0x06/0x07/0x08 profillarini qamraydi
(`specs/aether-q-v5.1/MAPPING.md`).

Vektorlar DETERMINISTIK: kalitlar va nonce'lar qat'iy urug'dan olinadi,
shuning uchun ikkala tomon aynan bir xil baytlarni kutadi.

    python tools/gen_des1_kat.py
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "apps" / "desktop" / "src"))

from distribos.aether_q import des1  # noqa: E402
from distribos.aether_q.vendor import kdf  # noqa: E402

OUTPUT = _ROOT / "tests" / "interoperability" / "des1_kat.json"


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def kdf_vectors() -> dict:
    """SHA3, HKDF, KMAC, cSHAKE — primitiv darajasi."""
    sha3_cases = []
    for name, raw in (
        ("empty", b""),
        ("short", b"distribos"),
        ("block", bytes(range(136))),
        ("long", b"A" * 500),
    ):
        sha3_cases.append({
            "name": name, "input": b64(raw), "sha3_256": b64(kdf.sha3_256(raw)),
        })

    hkdf_cases = []
    for salt, ikm, info, length in (
        (b"", b"secret", b"info", 32),
        (b"salt", b"secret", b"AETHER-Q-v5.1 master", 32),
        (bytes(range(16)), bytes(range(32)), des1.DES1_LABEL, 12),
        (b"long-salt" * 8, b"ikm" * 20, b"expand-64", 64),
    ):
        prk = kdf.hkdf_extract(salt, ikm)
        hkdf_cases.append({
            "salt": b64(salt), "ikm": b64(ikm), "info": b64(info), "length": length,
            "prk": b64(prk), "okm": b64(kdf.hkdf_expand(prk, info, length)),
        })

    kmac_cases = []
    for key, data, custom, length in (
        (bytes([0x40] * 32), b"ulush-tag-input", b"AETHER-Q-v5.1-SHARE", 32),
        (bytes(range(32)), b"", b"", 32),
        (b"k" * 32, b"DistribOS", b"DES1/tenant", 16),
    ):
        kmac_cases.append({
            "key": b64(key), "data": b64(data), "custom": b64(custom),
            "length": length, "out": b64(kdf.kmac256(key, data, length, custom=custom)),
        })

    cshake_cases = []
    for data, name, custom, length in (
        (b"input", b"N", b"S", 32),
        (b"", b"", b"", 32),
        (b"abc", b"KMAC", b"tenant", 64),
    ):
        cshake_cases.append({
            "data": b64(data), "name": b64(name), "custom": b64(custom),
            "length": length,
            "out": b64(kdf.cshake_256(data, length, name=name, custom=custom)),
        })

    return {
        "sha3": sha3_cases, "hkdf": hkdf_cases,
        "kmac256": kmac_cases, "cshake256": cshake_cases,
    }


def epoch_key_vectors() -> list[dict]:
    """DES-1 kalit ajratish — profil/epoch/key_id bind qilinganini qulflaydi."""
    cases = []
    root = bytes(range(32))
    tenant = b"tenant-demo-0001"
    for epoch, key_id, profile in ((1, 1, 0x01), (7, 3, 0x01), (7, 3, 0x03), (99, 42, 0x01)):
        keys = des1.derive_epoch_keys(root, tenant, epoch, key_id, profile)
        cases.append({
            "epoch_root_secret": b64(root), "tenant_id": b64(tenant),
            "epoch": epoch, "key_id": key_id, "profile_id": profile,
            "aead_key": b64(keys.aead_key), "aead_iv": b64(keys.aead_iv),
            "tenant_tag": b64(keys.tenant_tag),
        })
    return cases


def nonce_vectors() -> list[dict]:
    """nonce = seq XOR IV (little-endian, 96 bit)."""
    iv = bytes(range(12))
    return [
        {"sequence": sequence, "iv": b64(iv), "nonce": b64(des1._nonce(sequence, iv))}
        for sequence in (0, 1, 255, 256, 65535, 2**32, 2**48 - 1)
    ]


def header_vectors() -> list[dict]:
    """Header wire-format — bayt tartibini qulflaydi."""
    cases = []
    for epoch, key_id, sequence, content_type in ((1, 1, 1, 1), (7, 3, 42, 2), (99, 42, 65535, 6)):
        header = des1.Des1Header(
            version=des1.DES1_VERSION, profile_id=0x01, content_type=content_type,
            epoch=epoch, key_id=key_id,
            tenant_tag=bytes(range(16)), sender_device_id=bytes([0x11] * 16),
            sequence=sequence, rand=bytes([0xAA] * 6),
        )
        cases.append({
            "version": header.version, "profile_id": header.profile_id,
            "content_type": header.content_type, "epoch": header.epoch,
            "key_id": header.key_id, "tenant_tag": b64(header.tenant_tag),
            "sender_device_id": b64(header.sender_device_id),
            "sequence": header.sequence, "rand": b64(header.rand),
            "packed": b64(header.pack()),
        })
    return cases


def aead_vectors() -> list[dict]:
    """To'liq muhrlangan envelope — imzosiz qism (AEAD deterministik).

    Imzo KIRITILMAYDI: ML-DSA hedged, ya'ni har safar boshqa baytlar
    beradi. Kotlin tomoni imzoni TEKSHIRADI, lekin baytma-bayt
    solishtirmaydi.
    """
    root = bytes(range(32))
    tenant = b"tenant-demo-0001"
    keys = des1.derive_epoch_keys(root, tenant, 7, 3, 0x01)

    cases = []
    for sequence, plaintext in (
        (1, b""),
        (42, b'{"event":"ORDER_CREATED"}'),
        (65535, bytes(range(256)) * 4),
    ):
        header = des1.Des1Header(
            version=des1.DES1_VERSION, profile_id=0x01, content_type=1,
            epoch=7, key_id=3, tenant_tag=keys.tenant_tag,
            sender_device_id=bytes([0x11] * 16), sequence=sequence,
            rand=bytes([0xAA] * 6),
        )
        packed = header.pack()
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

        ciphertext = ChaCha20Poly1305(keys.aead_key).encrypt(
            des1._nonce(sequence, keys.aead_iv), plaintext, packed
        )
        cases.append({
            "epoch_root_secret": b64(root), "tenant_id": b64(tenant),
            "epoch": 7, "key_id": 3, "profile_id": 0x01,
            "sequence": sequence, "plaintext": b64(plaintext),
            "packed_header": b64(packed), "ciphertext": b64(ciphertext),
            "signed_bytes": b64(des1._signed_bytes(packed, ciphertext)),
        })
    return cases


def signature_vectors() -> list[dict]:
    """Python yaratgan HAQIQIY ML-DSA-65 imzolari.

    Kotlin tomoni ularni TEKSHIRA olishi kerak. Imzo baytlari
    solishtirilmaydi — ML-DSA hedged va har safar boshqa qiymat beradi.
    Muhimi: bir tomon imzolagan xabarni ikkinchisi qabul qilsin.
    """
    from distribos.aether_q.vendor import sig

    cases = []
    for label, message in (
        ("empty", b""),
        ("short", b"distribos"),
        ("des1-signed-bytes", des1.SIG_CONTEXT + bytes(range(66)) + bytes(32)),
        ("large", bytes(range(256)) * 8),
    ):
        public_key, private_key = sig.MLDSA65.keygen()
        signature = sig.MLDSA65.sign(private_key, message)
        assert sig.MLDSA65.verify(public_key, signature, message)
        cases.append({
            "name": label,
            "public_key": b64(public_key),
            "message": b64(message),
            "signature": b64(signature),
        })

    # Salbiy holat: imzo to'g'ri, lekin BOSHQA xabar uchun.
    public_key, private_key = sig.MLDSA65.keygen()
    signature = sig.MLDSA65.sign(private_key, b"asl xabar")
    cases.append({
        "name": "wrong-message",
        "public_key": b64(public_key),
        "message": b64(b"boshqa xabar"),
        "signature": b64(signature),
        "expect_valid": False,
    })

    # Salbiy holat: begona qurilma kaliti bilan tekshirish.
    foreign_public, _ = sig.MLDSA65.keygen()
    cases.append({
        "name": "foreign-key",
        "public_key": b64(foreign_public),
        "message": b64(b"asl xabar"),
        "signature": b64(signature),
        "expect_valid": False,
    })
    return cases


def event_batch_vectors() -> list[dict]:
    """Hodisa batch'ining SIM ustidagi CBOR shakli.

    Bu vektorlar aynan bir sinf xatoni qulflaydi: Python vaqtni ISO
    matn, Kotlin esa millisekund sifatida yuborsa, ikkala tomon ham
    "ishlaydi", lekin bir-birini TUSHUNMAYDI. Bunday nomuvofiqlik faqat
    ikki qurilma birga sinalganda ko'rinadi.
    """
    import cbor2

    cases = []
    for name, events in (
        ("single", [{
            "event_id": "01a02cfe-2a61-761b-924f-e90b9307cf10",
            "event_type": "ORDER_CREATED",
            "schema_version": 1,
            "aggregate_type": "Order",
            "aggregate_id": "01a02cfe-2a61-761b-924f-e90b9307cf11",
            "occurred_at_ms": 1787443200000,
            "logical_timestamp": "1787443200000.00000.6cc2a1b3",
            "device_sequence": 42,
            "payload": cbor2.dumps({"order_id": "o1", "total": 15000000}),
            "actor_id": "user-1",
        }]),
        ("batch-with-optionals-missing", [
            {
                "event_id": f"evt-{index:04d}",
                "event_type": "INVENTORY_MOVED",
                "schema_version": 1,
                "aggregate_type": "Inventory",
                "aggregate_id": f"prod-{index}",
                "occurred_at_ms": 1787443200000 + index * 1000,
                "logical_timestamp": f"1787443200{index:03d}.00000.dev00001",
                "device_sequence": index + 1,
                "payload": cbor2.dumps({"quantity": "10.5"}),
            }
            for index in range(3)
        ]),
    ):
        cases.append({
            "name": name,
            "events": [
                {
                    key: (b64(value) if isinstance(value, bytes) else value)
                    for key, value in event.items()
                }
                for event in events
            ],
            "cbor": b64(cbor2.dumps({"events": events})),
        })
    return cases


def main() -> int:
    payload = {
        "generated_by": "tools/gen_des1_kat.py",
        "des1_version": des1.DES1_VERSION,
        "aetherq_version": "5.1.0",
        "note": (
            "Python va Kotlin implementatsiyalarining baytma-bayt mosligini "
            "qulflaydi. Rasmiy AETHER-Q KAT'i EMAS."
        ),
        "kdf": kdf_vectors(),
        "epoch_keys": epoch_key_vectors(),
        "nonce": nonce_vectors(),
        "header": header_vectors(),
        "aead": aead_vectors(),
        "signatures": signature_vectors(),
        "event_batch": event_batch_vectors(),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Kotlin tomoni ham shu faylni o'qiydi — nusxa emas, bitta manba.
    android_copy = _ROOT / "apps" / "android" / "crypto" / "src" / "test" / "resources"
    android_copy.mkdir(parents=True, exist_ok=True)
    (android_copy / "des1_kat.json").write_text(
        OUTPUT.read_text(encoding="utf-8"), encoding="utf-8"
    )

    counts = {
        "kdf.sha3": len(payload["kdf"]["sha3"]),
        "kdf.hkdf": len(payload["kdf"]["hkdf"]),
        "kdf.kmac256": len(payload["kdf"]["kmac256"]),
        "kdf.cshake256": len(payload["kdf"]["cshake256"]),
        "epoch_keys": len(payload["epoch_keys"]),
        "nonce": len(payload["nonce"]),
        "header": len(payload["header"]),
        "aead": len(payload["aead"]),
        "signatures": len(payload["signatures"]),
        "event_batch": len(payload["event_batch"]),
    }
    print(f"KAT yozildi: {OUTPUT}")
    for name, count in counts.items():
        print(f"  {name:18s} {count}")
    print(f"Jami vektorlar: {sum(counts.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
